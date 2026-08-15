import pytest

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.scheduler import DeterministicScheduler
from qorchsim.errors import DuplicateEventError, PastEventError


def test_equal_time_order_is_phase_then_sequence() -> None:
    bus = EventBus()
    scheduler = DeterministicScheduler(bus, 100)
    observed: list[str] = []
    bus.subscribe("e", lambda event: observed.append(event.payload))
    scheduler.schedule_at(10, EventPhase.TIMEOUT, DomainEvent("3", "e", "timeout"))
    scheduler.schedule_at(10, EventPhase.PHYSICAL_ARRIVAL, DomainEvent("1", "e", "arrival"))
    scheduler.schedule_at(10, EventPhase.PROTOCOL, DomainEvent("2", "e", "protocol"))
    scheduler.run()
    assert observed == ["arrival", "protocol", "timeout"]


def test_duplicate_and_past_events_fail() -> None:
    bus = EventBus()
    scheduler = DeterministicScheduler(bus, 100)
    event = DomainEvent("x", "e", None)
    scheduler.schedule_at(5, EventPhase.PROTOCOL, event)
    with pytest.raises(DuplicateEventError):
        scheduler.schedule_at(6, EventPhase.PROTOCOL, event)
    scheduler.run()
    with pytest.raises(PastEventError):
        scheduler.schedule_at(4, EventPhase.PROTOCOL, DomainEvent("y", "e", None))
