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
        """
        Extract lines belonging to ALL occurrences of a section identified by a
        header like '## Allowed Write Scope' or '## Slice SLICE-A: Allowed Write Scope'.
        Scans the entire text and collects lines from every matching section.
        """
        lines = text.splitlines()
        result = []
        in_section = False
        for line in lines:
            stripped = line.strip()
            # Detect section start: any '##' line containing the header text
            if stripped.startswith("##") and header.lstrip("# ").strip() in stripped:
                in_section = True
                continue
            # End of section: next '##' header — restart scanning for next match
            if in_section and stripped.startswith("##"):
                in_section = False
                # Check if this new header also matches (e.g. second Allowed Write Scope)
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

    def execute(self, packet: str) -> bool:
        self._log("execution_started", "ok",
                  model=self.model, workspace=self.workspace)

        allowed = self._parse_scope(packet, "## Allowed Write Scope")

        if not allowed:
            self._log("no_allowed_files", "fail",
                      reason="No allowed files found in packet. Check section header formatting.")
            return False

        system_prompt = (
            "You are a strict code generation agent. Output ONLY code files in this format:"
            "\n===FILE:path/to/file.py==="
            "\n<complete code here>"
            "\n===END==="
            "\n"
            "\nCRITICAL RULES:"
            "\n1. If the user message has an '## Existing Context' section, that code contains"
            "\n   REAL interfaces (classes, methods, function signatures). You MUST use the exact"
            "\n   names, signatures, and import paths shown there. NEVER invent new methods or"
            "\n   classes that conflict with existing ones. NEVER modify frozen files."
            "\n2. Generate code compatible with existing interfaces. Check import names carefully."
            "\n3. For integration tests, mock or stub external dependencies if they don't exist yet."
            "\n4. Write complete, working code with proper imports."
            "\n5. Use the EXACT file paths from 'Allowed Write Scope' section."
        )

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": packet},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }

        self._log("llm_api_call_started", "ok", model=self.model)

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
            self._log("llm_api_call_failed", "fail",
                      reason=f"HTTP {e.code}", details=err[:200])
            return False
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

        files = self._extract_files(llm_output, allowed)
        if not files:
            files = self._extract_files_fallback(llm_output, allowed)
        if not files:
            self._log("no_code_blocks", "fail",
                      reason="No code blocks found in LLM response")
            return False

        for rel_path, code in files:
            abs_path = Path(self.workspace) / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(code, encoding="utf-8")
            self._log("file_written", "ok",
                      path=str(abs_path), size_bytes=len(code))

        self._log("execution_finished", "ok",
                  files_written=len(files),
                  paths=[str(Path(self.workspace) / f[0]) for f in files])
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


