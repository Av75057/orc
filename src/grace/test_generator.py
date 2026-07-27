import os
import json
import re
import time
import urllib.request
import urllib.error
from typing import List, Dict, Optional


class TestGenerator:
    def __init__(self, api_url: str, api_key: str, model: str, workspace: str):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.workspace = workspace

    def _read_source_files(self, src_files: List[str]) -> str:
        context = ""
        for path in src_files:
            full_path = os.path.join(self.workspace, path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    context += f"### FILE: {path}\n```python\n{f.read()}\n```\n\n"
        return context

    def generate(self, src_files: List[str], test_files: List[str], criteria: str = "") -> dict:
        source_code = self._read_source_files(src_files)
        if not source_code:
            return {"files_to_write": [], "logs": []}

        prompt = (
            "You are an expert Python test writer. Write pytest tests for the provided source code.\n"
            "CRITICAL RULES:\n"
            "1. Write tests that STRICTLY match actual interfaces (classes, methods, arguments).\n"
            "2. Do NOT modify source code. Only write test files.\n"
            "3. You MUST return valid JSON with schema: "
            '"files_to_write" (list of {"path": "...", "content": "..."})\n\n'
            f"## Acceptance Criteria:\n{criteria or 'N/A'}\n\n"
            f"## Source Code:\n{source_code}\n\n"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(self.api_url, data=payload, headers=headers, method="POST")

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    content = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    parsed = self._parse(content)
                    return parsed
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    time.sleep(10)
                else:
                    return {"files_to_write": [], "logs": []}
            except Exception:
                time.sleep(10)

        return {"files_to_write": [], "logs": []}

    def _parse(self, text: str) -> dict:
        m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text, re.DOTALL)
        if m:
            text = m.group(1)
        s = text.find("{")
        e = text.rfind("}")
        if s != -1 and e != -1 and e > s:
            text = text[s:e + 1]
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {"files_to_write": [], "logs": []}

