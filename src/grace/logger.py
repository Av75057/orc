import json
import sys
from datetime import datetime, timezone
from typing import Optional


class GraceLogger:
    def __init__(self, stream=sys.stdout):
        self._stream = stream

    def log(
        self,
        module: str,
        fn: str,
        block: str,
        event: str,
        result: str = "ok",
        trace_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ) -> dict:
        envelope = {
            "module": module,
            "fn": fn,
            "block": block,
            "event": event,
            "result": result,
            "trace_id": trace_id or "",
            "scenario_id": scenario_id or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._stream.write(json.dumps(envelope, ensure_ascii=False) + "\n")
        self._stream.flush()
        return envelope
