import abc
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional


class GraceWorker(abc.ABC):
    def __init__(self, workspace: Optional[str] = None):
        self.workspace = workspace or os.getcwd()

    def _log(self, event: str, result: str, **kwargs):
        entry = dict(
            timestamp=datetime.now(timezone.utc).isoformat(),
            module="M-WORKER",
            fn=self.name,
            block="EXECUTE",
            event=event,
            result=result,
            **kwargs,
        )
        print(json.dumps(entry), flush=True)

    @abc.abstractmethod
    def execute(self, packet: str, error_context: Optional[str] = None) -> bool:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...


class StubWorker(GraceWorker):
    def execute(self, packet: str, error_context: Optional[str] = None) -> bool:
        self._log("execution_started", "ok", details="stub worker, nothing to do")
        if error_context:
            self._log("repair_context_received", "ok", context=error_context[:100])
        self._log("execution_finished", "ok")
        return True

    @property
    def name(self) -> str:
        return "StubWorker"

