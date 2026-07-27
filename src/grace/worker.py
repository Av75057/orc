import abc
import os
from typing import Optional


class GraceWorker(abc.ABC):
    def __init__(self, workspace: Optional[str] = None):
        self.workspace = workspace or os.getcwd()

    @abc.abstractmethod
    def execute(self, packet: str) -> bool:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...


class StubWorker(GraceWorker):
    def execute(self, packet: str) -> bool:
        print(f"[WORKER] StubWorker (workspace={self.workspace}): nothing to execute")
        return True

    @property
    def name(self) -> str:
        return "StubWorker"

