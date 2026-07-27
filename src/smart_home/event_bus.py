"""
START_MODULE_CONTRACT: M-EVENTBUS
  purpose: Central event bus. Publish/subscribe by topic.
           Synchronous delivery. Subscriber error isolation.
  owns:
    - src/smart_home/event_bus.py
    - tests/test_event_bus.py
  inputs:
    - Event (from M-MODELS)
    - callback: Callable[[Event], None]
  outputs:
    - none (side-effect: event delivery)
  dependencies:
    - M-MODELS (Event)
    - Python stdlib: logging, collections
  side_effects:
    - Calls subscriber callbacks synchronously
    - Logs subscriber errors
  invariants:
    - INV-01: each event delivered to all subscribers exactly once
    - INV-04: unsubscribe removes subscriber completely
    - FAIL-01: subscriber error does not interrupt delivery
    - FAIL-02: publish to empty topic — no-op
    - FAIL-03: duplicate subscribe is ignored
  failure_policy:
    - Catches Exception in callback, logs, continues
  non_goals:
    - Async delivery
    - Event persistence
    - Subscriber prioritization
END_MODULE_CONTRACT: M-EVENTBUS
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

from src.smart_home.models import Event

logger = logging.getLogger(__name__)


class EventBus:
    """Publish/subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, topic: str, callback: Callable[[Event], None]) -> None:
        """Register callback on topic. Duplicates ignored (FAIL-03)."""
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Event], None]) -> None:
        """Remove callback from subscribers (INV-04)."""
        if callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)

    def publish(self, event: Event) -> None:
        """Deliver event to all subscribers (INV-01).

        Subscriber error does not interrupt delivery (FAIL-01).
        Publish to empty topic — no-op (FAIL-02).
        """
        for callback in list(self._subscribers.get(event.topic, [])):
            try:
                callback(event)
            except Exception:
                logger.exception("Subscriber error on topic=%s, continuing", event.topic)
