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
            "\n"
            "\nOutput ONLY valid JSON with this structure:"
            '\n{"files_to_write": [{"path": "src/file.py", "content": "code here"}], "logs": []}'
            "\n"
            "\nCRITICAL RULES:"
            "\n1. Write ONLY to files listed in 'Allowed Write Scope'."
            "\n2. Use REAL interfaces from 'Existing Context'. NEVER invent new methods."
            "\n3. Generate complete, working code with proper imports."
            "\n4. For test files, use pytest best practices."
            "\n5. Output ONLY the JSON object, no markdown wrappers, no explanations."
        )

    def _call_api(self, messages: list) -> dict:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096,
        }

        last_error = ""
        for attempt in range(MAX_API_RETRIES):
            try:
                req = urllib.request.Request(
                    self.api_url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                code = e.code
                if code in (429, 502, 503, 504):
                    self._log("rate_limit_retry", "retry",
                              attempt=attempt + 1, code=code)
                    time.sleep(RATE_LIMIT_SLEEP)
                    last_error = f"HTTP {code}"
                    continue
                self._log("llm_api_call_failed", "fail",
                          reason=f"HTTP {code}", details=err_body[:200])
                raise
            except Exception as e:
                self._log("llm_api_call_failed", "fail", reason=str(e))
                raise

        self._log("rate_limit_exceeded", "fail", reason=last_error)
        raise RuntimeError(f"LLM rate limit exceeded after {MAX_API_RETRIES} attempts")

    def _parse_llm_response(self, raw: str) -> dict:
        json_str = raw.strip()
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        if m:
            json_str = m.group(1).strip()
        return json.loads(json_str)

    def _write_files(self, files_data: list, allowed: List[str]):
        if not files_data:
            self._log("no_files_to_write", "fail", reason="Empty files_to_write")
            raise RuntimeError("LLM returned empty files_to_write")

        for entry in files_data:
            path = entry.get("path", "")
            content = entry.get("content", "")

            if path not in allowed:
                raise ScopeViolationError(
                    f"File '{path}' is not in Allowed Write Scope: {allowed}"
                )

            abs_path = Path(self.workspace) / path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            self._log("file_written", "ok",
                      path=str(abs_path), size_bytes=len(content))

    def execute(self, packet: str, error_context: Optional[str] = None) -> bool:
        self._log("execution_started", "ok",
                  model=self.model, workspace=self.workspace,
                  is_repair=(error_context is not None))

        allowed = self._parse_scope(packet, "## Allowed Write Scope")
        if not allowed:
            self._log("no_allowed_files", "fail",
                      reason="No allowed files found in packet")
            return False

        system_prompt = self._build_system_prompt()

        user_message = packet
        if error_context:
            user_message = (
                f"## PREVIOUS ATTEMPT FAILED\n"
                f"Your previous code failed with this error:\n"
                f"```\n{error_context}\n```\n"
                f"Please fix the code strictly within Allowed Write Scope.\n\n"
                f"{packet}"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        self._log("llm_api_call_started", "ok", model=self.model)

        try:
            response = self._call_api(messages)
        except Exception as e:
            self._log("llm_api_call_failed", "fail", reason=str(e))
            return False

        self._log("llm_api_call_finished", "ok",
                  usage=str(response.get("usage", {})))

        try:
            llm_output = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            self._log("llm_parse_failed", "fail",
                      reason="Unexpected API response format")
            return False

        try:
            parsed = self._parse_llm_response(llm_output)
        except (json.JSONDecodeError, ValueError) as e:
            self._log("malformed_llm_response", "fail", reason=str(e))
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

