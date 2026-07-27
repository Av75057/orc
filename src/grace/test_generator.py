import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional


class TestGenerator:
    def __init__(self, api_key: str, model: str, api_url: str, workspace: str = "."):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.workspace = workspace

    def _call_api(self, messages: list) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 8192,
        }
        for attempt in range(3):
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
                with urllib.request.urlopen(req, timeout=90) as resp:
                    response = json.loads(resp.read().decode("utf-8"))
                    return response["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(10 * (attempt + 1))
                continue
        raise RuntimeError("TestGenerator API retries exhausted")

    def generate(
        self,
        source_files: List[str],
        test_files: List[str],
        acceptance_criteria: str = "",
    ) -> dict:
        """
        Read source files, ask LLM to generate tests.
        Returns dict with 'files_to_write' list.
        """
        sources = {}
        for f in sorted(source_files):
            p = Path(self.workspace) / f
            if p.is_file():
                sources[f] = p.read_text(encoding="utf-8")
        if not sources:
            return {"files_to_write": [], "logs": []}

        sources_text = "\n\n".join(
            f"===FILE:{path}===\n{code}\n===END==="
            for path, code in sources.items()
        )

        system_prompt = (
            "You are a test generator. Given existing source code, write pytest tests."
            "\nOutput ONLY this format for each test file:"
            "\n===FILE:tests/test_name.py==="
            "\n<test code>"
            "\n===END==="
            "\nRules:"
            "\n1. Tests MUST match the exact class/method names from the source."
            "\n2. Use proper imports matching the source file structure."
            "\n3. Cover edge cases and normal usage."
        )

        user_message = (
            f"Write pytest tests for these source files.\n"
            f"Test files to create: {', '.join(test_files)}\n"
        )
        if acceptance_criteria:
            user_message += f"\nAcceptance criteria:\n{acceptance_criteria}\n"
        user_message += f"\n{sources_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        output = self._call_api(messages)
        return self._parse_response(output, test_files)

    def _parse_response(self, text: str, test_files: List[str]) -> dict:
        pattern = re.compile(r'===FILE:\s*(.+?)\s*===\s*\n(.*?)===END===', re.DOTALL)
        matches = pattern.findall(text)
        files = []
        for filepath, code in matches:
            filepath = filepath.strip()
            for tf in test_files:
                if filepath.endswith(tf.replace("tests/", "")) or filepath == tf:
                    files.append({"path": filepath, "content": code.strip()})
                    break
        # Fallback: just match the first N code blocks to test files
        if not files:
            blocks = re.findall(r'```(?:python)?\s*\n(.*?)\n```', text, re.DOTALL)
            if len(blocks) == len(test_files):
                for i, tf in enumerate(test_files):
                    files.append({"path": tf, "content": blocks[i].strip()})
        return {"files_to_write": files, "logs": []}

