import abc
from typing import Optional


class GraceWorker(abc.ABC):
    @abc.abstractmethod
    def execute(self, packet: str) -> bool:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...


class StubWorker(GraceWorker):
    def execute(self, packet: str) -> bool:
        print("[WORKER] StubWorker: nothing to execute")
        return True

    @property
    def name(self) -> str:
        return "StubWorker"
