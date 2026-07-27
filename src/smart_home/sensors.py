"""
START_MODULE_CONTRACT: M-TEMPSENSOR
  purpose: Generates "sensor.temperature" events with numeric value
  owns:
    - src/smart_home/sensors.py (TemperatureSensor)
    - tests/test_sensors.py
  inputs:
    - EventBus (from M-EVENTBUS)
    - value: float
  outputs:
    - Event("sensor.temperature", value) via EventBus
  dependencies:
    - M-MODELS (Event)
    - M-EVENTBUS (EventBus)
  side_effects:
    - Publishes event to EventBus
  invariants:
    - Topic always "sensor.temperature"
    - Payload — float
  failure_policy:
    - Propagates EventBus errors
  non_goals:
    - Calibration
    - Polling
END_MODULE_CONTRACT: M-TEMPSENSOR

START_MODULE_CONTRACT: M-MOTIONSENSOR
  purpose: Generates "sensor.motion" events with boolean value
  owns:
    - src/smart_home/sensors.py (MotionSensor)
    - tests/test_sensors.py
  inputs:
    - EventBus (from M-EVENTBUS)
    - motion: bool
  outputs:
    - Event("sensor.motion", motion) via EventBus
  dependencies:
    - M-MODELS (Event)
    - M-EVENTBUS (EventBus)
  side_effects:
    - Publishes event to EventBus
  invariants:
    - Topic always "sensor.motion"
    - Payload — bool
  failure_policy:
    - Propagates EventBus errors
  non_goals:
    - Debounce / timer
    - Sensitivity
END_MODULE_CONTRACT: M-MOTIONSENSOR
"""
from __future__ import annotations

from smart_home.event_bus import EventBus
from smart_home.models import Event


class TemperatureSensor:
    """Temperature sensor. Publishes sensor.temperature."""

    TOPIC = "sensor.temperature"

    def __init__(self, bus: EventBus, name: str = "temp-sensor") -> None:
        self._bus = bus
        self.name = name

    def read(self, value: float) -> None:
        """Publish current temperature value."""
        self._bus.publish(Event(topic=self.TOPIC, payload=value))


class MotionSensor:
    """Motion sensor. Publishes sensor.motion."""

    TOPIC = "sensor.motion"

    def __init__(self, bus: EventBus, name: str = "motion-sensor") -> None:
        self._bus = bus
        self.name = name

    def detect(self, motion: bool) -> None:
        """Publish motion detection event."""
        self._bus.publish(Event(topic=self.TOPIC, payload=motion))
