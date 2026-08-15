"""Simulation scheduler port and deterministic in-process implementation."""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Protocol

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.errors import DuplicateEventError, PastEventError
from qorchsim.types import DurationPs, SimTimePs


class EventScheduler(Protocol):
    """Schedule immutable domain events."""

    def now_ps(self) -> SimTimePs: ...

    def schedule_at(self, when_ps: SimTimePs, phase: EventPhase, event: DomainEvent) -> None: ...

    def schedule_after(self, delay_ps: DurationPs, phase: EventPhase, event: DomainEvent) -> None: ...


@dataclass(order=True, slots=True)
class _QueuedEvent:
    when_ps: int
    phase: int
    sequence: int
    event: DomainEvent = field(compare=False)


class DeterministicScheduler:
    """Small virtual-time scheduler used by tests and as a portable fallback.

    The production SeQUeNCe adapter exposes the same port. Keeping this implementation
    allows all domain and protocol tests to run without importing SeQUeNCe.
    """

    def __init__(self, event_bus: EventBus, stop_time_ps: int) -> None:
        self.event_bus = event_bus
        self.stop_time_ps = stop_time_ps
        self._now = 0
        self._queue: list[_QueuedEvent] = []
        self._sequence = itertools.count()
        self._ids: set[str] = set()
        self.dispatched = 0

    def now_ps(self) -> SimTimePs:
        return SimTimePs(self._now)

    def schedule_at(self, when_ps: SimTimePs, phase: EventPhase, event: DomainEvent) -> None:
        when = int(when_ps)
        if when < self._now:
            raise PastEventError(f"cannot schedule {event.event_id} at {when}; now={self._now}")
        if event.event_id in self._ids:
            raise DuplicateEventError(event.event_id)
        self._ids.add(event.event_id)
        heapq.heappush(self._queue, _QueuedEvent(when, int(phase), next(self._sequence), event))

    def schedule_after(self, delay_ps: DurationPs, phase: EventPhase, event: DomainEvent) -> None:
        delay = int(delay_ps)
        if delay < 0:
            raise PastEventError("negative delay")
        self.schedule_at(SimTimePs(self._now + delay), phase, event)

    def run(self) -> None:
        while self._queue:
            item = heapq.heappop(self._queue)
            if item.when_ps >= self.stop_time_ps:
                heapq.heappush(self._queue, item)
                break
            self._ids.remove(item.event.event_id)
            self._now = item.when_ps
            self.event_bus.publish(item.event)
            self.dispatched += 1

    @property
    def pending_count(self) -> int:
        return len(self._queue)
