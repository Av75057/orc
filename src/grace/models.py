from dataclasses import dataclass, field
from typing import List


@dataclass
class Wave:
    id: str
    goal: str
    modules: List[str] = field(default_factory=list)
    allowed_write_scope: List[str] = field(default_factory=list)
    frozen_scope: List[str] = field(default_factory=list)
    must_preserve: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)


@dataclass
class Phase:
    id: str
    goal: str
    waves: List[Wave] = field(default_factory=list)


@dataclass
class DevelopmentPlan:
    phases: List[Phase] = field(default_factory=list)
