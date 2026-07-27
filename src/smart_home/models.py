"""
START_MODULE_CONTRACT: M-MODELS
  purpose: Shared data models for Smart Home system
  owns:
    - src/smart_home/models.py
  inputs:
    - none (leaf module)
  outputs:
    - Event (frozen dataclass: topic, payload)
    - Device (base class: name, is_on)
  dependencies:
    - Python stdlib: dataclasses, typing
  side_effects:
    - none
  invariants:
    - INV-06: Event immutable after creation
    - Device.is_on — bool, defaults to False
  failure_policy:
    - ValueError on empty topic
  non_goals:
    - No business logic
    - Does not import other smart_home modules
END_MODULE_CONTRACT: M-MODELS
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    """Immutable event for the bus."""

    topic: str
    payload: Any

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("Event topic must not be empty")


class Device:
    """Base smart home device."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.is_on = False
