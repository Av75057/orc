"""
START_MODULE_CONTRACT: M-THERMOSTAT
  purpose: Subscribes to sensor.temperature. Heater ON when
           temp < threshold, OFF when temp >= threshold.
  owns:
    - src/smart_home/actuators.py (Thermostat)
    - tests/test_actuators.py
  inputs:
    - EventBus (from M-EVENTBUS)
    - threshold: float (default 20.0)
  outputs:
    - is_on: bool (heater state)
  dependencies:
    - M-MODELS (Event, Device)
    - M-EVENTBUS (EventBus)
  side_effects:
    - Subscribes to EventBus on creation
    - Mutates self.is_on
  invariants:
    - INV-02: is_on == True <=> last temp < threshold
  failure_policy:
    - Error in _on_temperature logged by EventBus (FAIL-01)
  non_goals:
    - Hysteresis
    - Schedule
    - PID controller
END_MODULE_CONTRACT: M-THERMOSTAT

START_MODULE_CONTRACT: M-LIGHTBULB
  purpose: Subscribes to sensor.motion. Light ON when
           motion == True, OFF when motion == False.
  owns:
    - src/smart_home/actuators.py (LightBulb)
    - tests/test_actuators.py
  inputs:
    - EventBus (from M-EVENTBUS)
  outputs:
    - is_on: bool (light state)
  dependencies:
    - M-MODELS (Event, Device)
    - M-EVENTBUS (EventBus)
  side_effects:
    - Subscribes to EventBus on creation
    - Mutates self.is_on
  invariants:
    - INV-03: is_on == True <=> last motion == True
  failure_policy:
    - Error in _on_motion logged by EventBus (FAIL-01)
  non_goals:
    - Auto-off timer
    - Dimming
END_MODULE_CONTRACT: M-LIGHTBULB
"""
from __future__ import annotations

from src.smart_home.event_bus import EventBus
from src.smart_home.models import Device, Event
from src.smart_home.sensors import MotionSensor, TemperatureSensor


class Thermostat(Device):
    """Thermostat. Heater ON when temp < threshold."""

    def __init__(self, bus: EventBus, threshold: float = 20.0, name: str = "thermostat") -> None:
        super().__init__(name=name)
        self.threshold = threshold
        bus.subscribe(TemperatureSensor.TOPIC, self._on_temperature)

    def _on_temperature(self, event: Event) -> None:
        """Handler: is_on = (payload < threshold). INV-02."""
        self.is_on = event.payload < self.threshold


class LightBulb(Device):
    """Light bulb. Light ON when motion == True."""

    def __init__(self, bus: EventBus, name: str = "light-bulb") -> None:
        super().__init__(name=name)
        bus.subscribe(MotionSensor.TOPIC, self._on_motion)

    def _on_motion(self, event: Event) -> None:
        """Handler: is_on = payload. INV-03."""
        self.is_on = bool(event.payload)
