from __future__ import annotations
import pytest
from src.smart_home.event_bus import EventBus
from src.smart_home.sensors import TemperatureSensor, MotionSensor


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


class TestTemperatureSensor:
    def test_read_publishes(self, bus: EventBus) -> None:
        r = []
        bus.subscribe(TemperatureSensor.TOPIC, r.append)
        TemperatureSensor(bus).read(22.5)
        assert len(r) == 1
        assert r[0].topic == "sensor.temperature"
        assert r[0].payload == 22.5

    def test_multiple_values(self, bus: EventBus) -> None:
        r = []
        bus.subscribe(TemperatureSensor.TOPIC, r.append)
        s = TemperatureSensor(bus)
        for v in [15.0, 20.0, 25.0]:
            s.read(v)
        assert [e.payload for e in r] == [15.0, 20.0, 25.0]

    def test_topic_constant(self) -> None:
        assert TemperatureSensor.TOPIC == "sensor.temperature"


class TestMotionSensor:
    def test_detect_true(self, bus: EventBus) -> None:
        r = []
        bus.subscribe(MotionSensor.TOPIC, r.append)
        MotionSensor(bus).detect(True)
        assert r[0].payload is True

    def test_detect_false(self, bus: EventBus) -> None:
        r = []
        bus.subscribe(MotionSensor.TOPIC, r.append)
        MotionSensor(bus).detect(False)
        assert r[0].payload is False

    def test_topic_constant(self) -> None:
        assert MotionSensor.TOPIC == "sensor.motion"


class TestIsolation:
    def test_temp_not_motion(self, bus: EventBus) -> None:
        r = []
        bus.subscribe(MotionSensor.TOPIC, r.append)
        TemperatureSensor(bus).read(22.0)
        assert len(r) == 0

    def test_motion_not_temp(self, bus: EventBus) -> None:
        r = []
        bus.subscribe(TemperatureSensor.TOPIC, r.append)
        MotionSensor(bus).detect(True)
        assert len(r) == 0
