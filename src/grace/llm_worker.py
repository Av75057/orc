import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Tuple, Optional
from src.grace.worker import GraceWorker

MAX_API_RETRIES = 3
RATE_LIMIT_SLEEP = 10


class ScopeViolationError(Exception):
    pass


class LLMWorker(GraceWorker):
    def __init__(self, workspace: Optional[str] = None):
        super().__init__(workspace)
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.api_url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")

    @property
    def name(self) -> str:
        return f"LLMWorker({self.model})"

    def _section_lines(self, text: str, header: str) -> List[str]:
        lines = text.splitlines()
        result = []
        in_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("##") and header.lstrip("# ").strip() in stripped:
                in_section = True
                continue
            if in_section and stripped.startswith("##"):
                in_section = False
                if header.lstrip("# ").strip() in stripped:
                    in_section = True
                    continue
            if in_section and stripped:
                result.append(stripped)
        return result

    def _parse_scope(self, text: str, header: str) -> List[str]:
        items = []
        for line in self._section_lines(text, header):
            m = re.match(r'^- `(.+)`$', line)
            if m:
                items.append(m.group(1))
        return items

    def _build_system_prompt(self) -> str:
        return (
            "You are a strict code generation agent."
            "\nUse this format for each file:"
            "\n===FILE:path/to/file.py==="
            "\n<complete code here>"
            "\n===END==="
            "\n"
            "\nCRITICAL RULES:"
            "\n1. Write ONLY to files listed in Allowed Write Scope."
            "\n2. Use REAL interfaces from Existing Context. NEVER invent new methods."
            "\n3. Generate complete, working code with proper imports."
            "\n4. For test files, use pytest best practices."
        )

    def _call_api(self, messages: list) -> dict:
        body = {"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": 8192, "response_format": {"type": "json_object"}}
        for attempt in range(MAX_API_RETRIES):
            try:
                req = urllib.request.Request(
                    self.api_url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code in (429, 500, 502, 503, 504):
                    wait = RATE_LIMIT_SLEEP * (attempt + 1)
                    self._log("api_retry", "retry", attempt=attempt + 1, code=e.code, wait_s=wait)
                    time.sleep(wait)
                    if attempt < MAX_API_RETRIES - 1:
                        continue
                raise RuntimeError(f"LLM_API_HTTP_{e.code}: {err_body[:200]}")
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                wait = RATE_LIMIT_SLEEP * (attempt + 1)
                self._log("api_retry", "retry", attempt=attempt + 1, reason=str(e)[:100], wait_s=wait)
                time.sleep(wait)
                if attempt < MAX_API_RETRIES - 1:
                    continue
                raise RuntimeError(f"LLM_API_TIMEOUT: {e}")
        raise RuntimeError("LLM_RATE_LIMIT_EXHAUSTED: Max API retries reached")

    def _extract_files_from_text(self, output: str) -> list:
        result = []
        # P1: ===FILE:path=== code ===END===
        p1 = re.compile(r'''===FILE:\s*(.+?)\s*===\s*
(.*?)===END===''', re.DOTALL)
        for filepath, code in p1.findall(output):
            filepath = filepath.strip()
            if filepath.endswith(('.py', '.md', '.txt', '.xml', '.json', '.yml', '.yaml')):
                result.append((filepath, code.strip()))
        if result:
            return result
        # P2: ===FILE:path=== followed by ```python ... ```
        p2 = re.compile(r'''===FILE:\s*(.+?)\s*===.*?
```(?:python)?\s*
(.*?)
```''', re.DOTALL)
        for filepath, code in p2.findall(output):
            filepath = filepath.strip()
            if filepath.endswith(('.py', '.md', '.txt')):
                result.append((filepath, code.strip()))
        return result

    def _parse_llm_response(self, raw: str) -> dict:
        text = raw.strip()
        # Strip markdown json wrappers
        m = re.search(r'''```(?:json)?\s*
([\s\S]*?)
```''', text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        # Find { and }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
        # Fallback: ===FILE=== format
        files = self._extract_files_from_text(raw)
        if files:
            return {"files_to_write": [{"path": p, "content": c} for p, c in files], "logs": []}
        raise ValueError(f"Cannot parse LLM response. RAW(first 500): {raw[:500]}")

    def _write_files(self, files_data: list, allowed: List[str]):
        if not files_data:
            raise RuntimeError("LLM returned empty files_to_write")
        for entry in files_data:
            path = entry.get("path", "")
            content = entry.get("content", "")
            if path not in allowed:
                raise ScopeViolationError(f"File '{path}' is not in Allowed Write Scope: {allowed}")
            abs_path = Path(self.workspace) / path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            self._log("file_written", "ok", path=str(abs_path), size_bytes=len(content))

    def execute(self, packet: str, error_context: Optional[str] = None) -> bool:
        self._log("execution_started", "ok", model=self.model, workspace=self.workspace, is_repair=(error_context is not None))

        allowed = self._parse_scope(packet, "## Allowed Write Scope")
        if not allowed:
            self._log("no_allowed_files", "fail", reason="No allowed files found in packet")
            return False

        system_prompt = self._build_system_prompt()
        user_message = packet
        if error_context:
            user_message = f"## PREVIOUS ATTEMPT FAILED\nYour previous code failed with this error:\n```\n{error_context}\n```\nPlease fix the code strictly within Allowed Write Scope.\n\n{packet}"

        messages = [
            {"role": "system", "content": system_prompt + " You MUST output JSON. JSON schema: {"files_to_write": [{"path": "...", "content": "..."}], "logs": [{}]}"},
            {"role": "user", "content": user_message},
        ]
        self._log("llm_api_call_started", "ok", model=self.model)

        try:
            response = self._call_api(messages)
        except RuntimeError as e:
            msg = str(e)
            if "LLM_API_HTTP" in msg or "LLM_API_TIMEOUT" in msg:
                raise
            self._log("llm_api_call_failed", "fail", reason=msg)
            return False

        self._log("llm_api_call_finished", "ok", usage=str(response.get("usage", {})))

        try:
            llm_output = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            self._log("llm_parse_failed", "fail", reason="Unexpected API response format")
            return False

        try:
            parsed = self._parse_llm_response(llm_output)
        except ValueError as e:
            self._log("malformed_llm_response", "fail", reason=str(e), raw_response=llm_output[:1000])
            return False

        if not parsed.get("files_to_write"):
            self._log("no_files_to_write", "fail", reason="LLM returned empty response")
            return False

        try:
            self._write_files(parsed.get("files_to_write", []), allowed)
        except ScopeViolationError as e:
            self._log("scope_violation", "fail", reason=str(e))
            return False
        except RuntimeError as e:
            self._log("write_failed", "fail", reason=str(e))
            return False

        self._log("execution_finished", "ok")
        return True




