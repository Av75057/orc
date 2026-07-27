from __future__ import annotations
import pytest
from src.smart_home.actuators import Thermostat, LightBulb
from src.smart_home.event_bus import EventBus
from src.smart_home.models import Event
from src.smart_home.sensors import MotionSensor, TemperatureSensor


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


class TestThermostat:
    def test_initial_off(self, bus: EventBus) -> None:
        assert Thermostat(bus).is_on is False

    def test_cold_on(self, bus: EventBus) -> None:
        t = Thermostat(bus, threshold=20.0)
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=15.0))
        assert t.is_on is True

    def test_warm_off(self, bus: EventBus) -> None:
        t = Thermostat(bus, threshold=20.0)
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=25.0))
        assert t.is_on is False

    def test_exact_threshold_off(self, bus: EventBus) -> None:
        t = Thermostat(bus, threshold=20.0)
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=20.0))
        assert t.is_on is False

    def test_transitions(self, bus: EventBus) -> None:
        t = Thermostat(bus, threshold=20.0)
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=15.0))
        assert t.is_on is True
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=25.0))
        assert t.is_on is False

    def test_ignores_motion(self, bus: EventBus) -> None:
        t = Thermostat(bus)
        bus.publish(Event(topic=MotionSensor.TOPIC, payload=True))
        assert t.is_on is False


class TestLightBulb:
    def test_initial_off(self, bus: EventBus) -> None:
        assert LightBulb(bus).is_on is False

    def test_motion_on(self, bus: EventBus) -> None:
        l = LightBulb(bus)
        bus.publish(Event(topic=MotionSensor.TOPIC, payload=True))
        assert l.is_on is True

    def test_motion_off(self, bus: EventBus) -> None:
        l = LightBulb(bus)
        bus.publish(Event(topic=MotionSensor.TOPIC, payload=False))
        assert l.is_on is False

    def test_transitions(self, bus: EventBus) -> None:
        l = LightBulb(bus)
        bus.publish(Event(topic=MotionSensor.TOPIC, payload=True))
        assert l.is_on is True
        bus.publish(Event(topic=MotionSensor.TOPIC, payload=False))
        assert l.is_on is False

    def test_ignores_temp(self, bus: EventBus) -> None:
        l = LightBulb(bus)
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=15.0))
        assert l.is_on is False


class TestIsolation:
    def test_thermostat_not_motion(self, bus: EventBus) -> None:
        t = Thermostat(bus)
        LightBulb(bus)
        bus.publish(Event(topic=MotionSensor.TOPIC, payload=True))
        assert t.is_on is False

    def test_light_not_temp(self, bus: EventBus) -> None:
        t = Thermostat(bus)
        l = LightBulb(bus)
        bus.publish(Event(topic=TemperatureSensor.TOPIC, payload=15.0))
        assert t.is_on is True
        assert l.is_on is False
