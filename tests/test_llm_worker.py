import json
import pytest
from unittest.mock import patch, MagicMock
from src.grace.llm_worker import LLMWorker


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
        assert "Database" in user_content
        assert "def connect" in user_content

    @patch("src.grace.llm_worker.urllib.request.urlopen")
    def test_no_context_still_works(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "===FILE:src/app.py===\nprint('ok')\n===END==="}}],
            "usage": {"total_tokens": 100},
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        packet = """# Controller Packet

## Allowed Write Scope
- `src/app.py`

## Expected Evidence
- Tests pass
"""

        worker = LLMWorker(workspace="/tmp/test")
        worker.api_key = "sk-test"
        worker.api_url = "https://api.openai.com/v1/chat/completions"

        result = worker.execute(packet)
        assert result is True
