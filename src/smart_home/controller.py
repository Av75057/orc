"""
START_MODULE_CONTRACT: M-CONTROLLER-SH
  purpose: Creates EventBus, registers sensors and actuators,
           provides integration scenarios.
  owns:
    - src/smart_home/controller.py
    - tests/test_integration.py
  inputs:
    - none (creates all dependencies)
  outputs:
    - get_state() -> dict with device states
  dependencies:
    - M-MODELS, M-EVENTBUS, M-TEMPSENSOR, M-MOTIONSENSOR, M-THERMOSTAT, M-LIGHTBULB
  side_effects:
    - Creates EventBus and all devices
    - Publishes events via sensors
  invariants:
    - INV-05: does not modify EventBus directly
    - All interaction through publish/subscribe
  failure_policy:
    - Propagates initialization errors
  non_goals:
    - Extended scenarios (schedules, scenes)
    - State persistence
END_MODULE_CONTRACT: M-CONTROLLER-SH
"""
from __future__ import annotations

from src.smart_home.actuators import LightBulb, Thermostat
from src.smart_home.event_bus import EventBus
from src.smart_home.sensors import MotionSensor, TemperatureSensor


class SmartHomeController:
    """Smart home coordinator."""

    def __init__(self) -> None:
        self.bus = EventBus()
        self.temp_sensor = TemperatureSensor(self.bus)
        self.motion_sensor = MotionSensor(self.bus)
        self.thermostat = Thermostat(self.bus)
        self.light_bulb = LightBulb(self.bus)

    def simulate_cold_temp(self, value: float = 15.0) -> None:
        """Publish low temperature → Thermostat turns ON."""
        self.temp_sensor.read(value)

    def simulate_motion(self, motion: bool = True) -> None:
        """Publish motion → LightBulb turns ON."""
        self.motion_sensor.detect(motion)

    def simulate_all_clear(self) -> None:
        """Publish clear → all actuators turn OFF."""
        self.temp_sensor.read(25.0)
        self.motion_sensor.detect(False)

    def get_state(self) -> dict:
        """Return current state of all devices."""
        return {
            "thermostat": {"name": self.thermostat.name, "is_on": self.thermostat.is_on},
            "light_bulb": {"name": self.light_bulb.name, "is_on": self.light_bulb.is_on},
        }
