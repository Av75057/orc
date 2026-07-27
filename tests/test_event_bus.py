from __future__ import annotations
import pytest
from src.smart_home.event_bus import EventBus
from src.smart_home.models import Event


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def event() -> Event:
    return Event(topic="test.topic", payload=42)


class TestDelivery:
    def test_single_subscriber(self, bus: EventBus, event: Event) -> None:
        received: list[Event] = []
        bus.subscribe("test.topic", received.append)
        bus.publish(event)
        assert len(received) == 1
        assert received[0] is event

    def test_multiple_subscribers(self, bus: EventBus, event: Event) -> None:
        a: list[Event] = []
        b: list[Event] = []
        c: list[Event] = []
        bus.subscribe("test.topic", a.append)
        bus.subscribe("test.topic", b.append)
        bus.subscribe("test.topic", c.append)
        bus.publish(event)
        assert len(a) == 1 and len(b) == 1 and len(c) == 1

    def test_other_topic_not_called(self, bus: EventBus, event: Event) -> None:
        received: list[Event] = []
        bus.subscribe("other.topic", received.append)
        bus.publish(event)
        assert len(received) == 0

    def test_multiple_events_in_order(self, bus: EventBus) -> None:
        received: list[Event] = []
        bus.subscribe("seq", received.append)
        for v in [1, 2, 3]:
            bus.publish(Event(topic="seq", payload=v))
        assert [e.payload for e in received] == [1, 2, 3]


class TestUnsubscribe:
    def test_unsubscribe_removes(self, bus: EventBus, event: Event) -> None:
        received: list[Event] = []
        fn = received.append
        bus.subscribe("test.topic", fn)
        bus.unsubscribe("test.topic", fn)
        bus.publish(event)
        assert len(received) == 0

    def test_unsubscribe_nonexistent(self, bus: EventBus, event: Event) -> None:
        received: list[Event] = []
        fn = received.append
        bus.unsubscribe("x", fn)  # unsubscribe not-subscribed — noop
        bus.subscribe("x", fn)
        bus.publish(Event(topic="x", payload=42))
        assert len(received) == 1

    def test_unsubscribe_one_of_many(self, bus: EventBus, event: Event) -> None:
        a: list[Event] = []
        b: list[Event] = []
        fn_a = a.append
        fn_b = b.append
        bus.subscribe("test.topic", fn_a)
        bus.subscribe("test.topic", fn_b)
        bus.unsubscribe("test.topic", fn_a)
        bus.publish(event)
        assert len(a) == 0 and len(b) == 1


class TestErrorIsolation:
    def test_failing_does_not_block(self, bus: EventBus, event: Event) -> None:
        received_a: list[Event] = []
        received_b: list[Event] = []
        bus.subscribe("test.topic", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        bus.subscribe("test.topic", received_a.append)
        bus.subscribe("test.topic", received_b.append)
        bus.publish(event)
        assert len(received_a) == 1 and len(received_b) == 1

    def test_all_fail(self, bus: EventBus, event: Event) -> None:
        bus.subscribe("test.topic", lambda e: (_ for _ in ()).throw(ValueError()))
        bus.subscribe("test.topic", lambda e: (_ for _ in ()).throw(TypeError()))
        bus.publish(event)


class TestDuplicate:
    def test_duplicate_ignored(self, bus: EventBus, event: Event) -> None:
        received: list[Event] = []
        fn = received.append
        bus.subscribe("test.topic", fn)
        bus.subscribe("test.topic", fn)
        bus.publish(event)
        assert len(received) == 1


class TestEmptyTopic:
    def test_no_subscribers_no_error(self, bus: EventBus) -> None:
        bus.publish(Event(topic="empty", payload=None))

    def test_after_unsubscribed(self, bus: EventBus) -> None:
        received: list[Event] = []
        fn = received.append
        bus.subscribe("test.topic", fn)
        bus.unsubscribe("test.topic", fn)
        bus.publish(Event(topic="test.topic", payload=1))
        assert len(received) == 0


class TestImmutability:
    def test_frozen(self) -> None:
        event = Event(topic="t", payload=1)
        with pytest.raises(AttributeError):
            event.topic = "x"

    def test_empty_topic(self) -> None:
        with pytest.raises(ValueError, match="topic"):
            Event(topic="", payload=1)



