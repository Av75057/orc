from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    topic: str
    payload: Any


class Device:
    def __init__(self, name: str):
        self.name = name
        self.is_on = False

