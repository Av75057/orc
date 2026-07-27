import json
import pytest
from unittest.mock import patch, MagicMock
from src.grace.llm_worker import LLMWorker


class TestSectionParsing:
    def test_parses_standard_section(self):
        w = LLMWorker()
        lines = w._section_lines(
            "## Allowed Write Scope\n- `a.py`\n- `b.py`\n## Next",
            "## Allowed Write Scope"
        )
        assert "- `a.py`" in lines
        assert "- `b.py`" in lines

    def test_parses_section_with_slice_in_header(self):
        w = LLMWorker()
        packet = """# Controller Packet

## Slice SLICE-A-1: Discount Module

## Allowed Write Scope
- `src/discount.py`
- `tests/test_discount.py`

## Slice SLICE-A-2: Notifier Module

## Allowed Write Scope
- `src/notifier.py`
- `tests/test_notifier.py`

## Verification
- `pytest`
"""
        allowed = w._parse_scope(packet, "## Allowed Write Scope")
        assert "src/discount.py" in allowed
        assert "tests/test_discount.py" in allowed
        assert "src/notifier.py" in allowed
        assert "tests/test_notifier.py" in allowed
        assert len(allowed) == 4

    def test_parses_slice_inline_header(self):
        w = LLMWorker()
        packet = """## Slice SLICE-B: Allowed Write Scope
- `src/module.py`
## Next Section
- other stuff
"""
        allowed = w._parse_scope(packet, "## Allowed Write Scope")
        assert "src/module.py" in allowed

    def test_empty_section_returns_empty(self):
        w = LLMWorker()
        lines = w._section_lines("## Allowed Write Scope\n## Next", "## Allowed Write Scope")
        assert lines == []

    def test_missing_section_returns_empty(self):
        w = LLMWorker()
        lines = w._section_lines("## Other\nstuff\n## Next", "## Allowed Write Scope")
        assert lines == []


class TestLLMWorkerContext:
    @patch("src.grace.llm_worker.urllib.request.urlopen")
    def test_existing_context_in_payload(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "===FILE:src/app.py===\nprint('ok')\n===END==="}}],
            "usage": {"total_tokens": 100},
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        packet = """# Controller Packet

## Allowed Write Scope
- `src/app.py`

## Existing Context (Read-Only)
### `src/db.py`
```
class Database:
    def connect(self): pass
```

## Expected Evidence
- Tests pass
"""

        worker = LLMWorker(workspace="/tmp/test")
        worker.api_key = "sk-test"
        worker.api_url = "https://api.openai.com/v1/chat/completions"

        result = worker.execute(packet)
        assert result is True

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        sent_body = json.loads(req.data)
        user_content = sent_body["messages"][1]["content"]
        assert "Existing Context" in user_content

    @patch("src.grace.llm_worker.urllib.request.urlopen")
    def test_prompt_has_strict_rules(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "===FILE:src/app.py===\nprint('ok')\n===END==="}}],
            "usage": {},
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        packet = """## Allowed Write Scope
- `src/app.py`
"""
        worker = LLMWorker()
        worker.api_key = "sk"
        worker.api_url = "http://test/api"
        worker.execute(packet)

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data)
        system = body["messages"][0]["content"]
        assert "REAL interfaces" in system
        assert "Existing Context" in system
        assert "REAL interfaces" in system

    @patch("src.grace.llm_worker.urllib.request.urlopen")
    def test_no_allowed_files_returns_false(self, mock_urlopen):
        packet = """## Allowed Write Scope
## Next Section
"""
        worker = LLMWorker()
        worker.api_key = "sk"
        worker.api_url = "http://test/api"
        result = worker.execute(packet)
        assert result is False


