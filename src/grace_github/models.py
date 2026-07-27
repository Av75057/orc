from dataclasses import dataclass
from typing import Optional


@dataclass
class PRConfig:
    title: str
    body: str
    head: str
    base: str = "main"
