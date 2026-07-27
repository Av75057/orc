import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Tuple, Optional
from src.grace.worker import GraceWorker


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
            if line.strip().startswith(header):
                in_section = True
                continue
            if in_section and line.startswith("##"):
                break
            if in_section and line.strip():
                result.append(line.strip())
        return result

    def _parse_scope(self, text: str, header: str) -> List[str]:
        items = []
        for line in self._section_lines(text, header):
            m = re.match(r'^- `(.+)`$', line)
            if m:
                items.append(m.group(1))
        return items

    def execute(self, packet: str) -> bool:
        print(f"[LLMWorker] Using model={self.model}, workspace={self.workspace}", file=sys.stderr)

        allowed = self._parse_scope(packet, "## Allowed Write Scope")

        if not allowed:
            print("[LLMWorker] No allowed files found", file=sys.stderr)
            return True

        system_prompt = """You are a code generation agent. Output ONLY code files in this format:

===FILE:path/to/file.py===
<complete code here>
===END===

Write complete, working code. Use the exact file paths from the Allowed Write Scope."""

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": packet},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                response = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            print(f"[LLMWorker] HTTP {e.code}: {err}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[LLMWorker] Error: {e}", file=sys.stderr)
            return False

        try:
            llm_output = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            print("[LLMWorker] Unexpected API response", file=sys.stderr)
            return False

        files = self._extract_files(llm_output, allowed)
        if not files:
            files = self._extract_files_fallback(llm_output, allowed)
        if not files:
            print("[LLMWorker] No code blocks found in response", file=sys.stderr)
            return False

        for rel_path, code in files:
            abs_path = Path(self.workspace) / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(code, encoding="utf-8")
            print(f"[LLMWorker] Wrote {abs_path} ({len(code)} bytes)", file=sys.stderr)

        return True

    def _extract_files(self, output: str, allowed: List[str]) -> List[Tuple[str, str]]:
        pattern = re.compile(r'===FILE:(.+?)===\n(.*?)===END===', re.DOTALL)
        matches = pattern.findall(output)
        result = []
        for filepath, code in matches:
            filepath = filepath.strip()
            if filepath in allowed:
                result.append((filepath, code.strip()))
        return result

    def _extract_files_fallback(self, output: str, allowed: List[str]) -> List[Tuple[str, str]]:
        pattern = re.compile(r'```(?:python)?\n(.*?)```', re.DOTALL)
        matches = pattern.findall(output)
        if len(matches) == len(allowed):
            return [(allowed[i], code.strip()) for i, code in enumerate(matches)]
        return []

