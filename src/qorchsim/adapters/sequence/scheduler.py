"""SeQUeNCe-backed implementation of the event scheduler port."""

from __future__ import annotations

from collections import defaultdict

from sequence.kernel.event import Event  # type: ignore[import-untyped]
from sequence.kernel.process import Process  # type: ignore[import-untyped]
from sequence.kernel.timeline import Timeline  # type: ignore[import-untyped]

from qorchsim.adapters.sequence.event_pump import SequenceEventPump
from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase, encode_priority
from qorchsim.errors import PastEventError
from qorchsim.types import DurationPs, SimTimePs


class SequenceEventScheduler:
    """Use SeQUeNCe's integer-picosecond heap as the simulation clock."""

    def __init__(self, event_bus: EventBus, stop_time_ps: int) -> None:
        self.timeline = Timeline(stop_time=stop_time_ps, formalism="density_matrix")
        self.pump = SequenceEventPump("qorchsim-event-pump", self.timeline, event_bus)
        self._sequences: dict[tuple[int, EventPhase], int] = defaultdict(int)
        self._initialized = False

    def now_ps(self) -> SimTimePs:
        return SimTimePs(self.timeline.now())

    def schedule_at(self, when_ps: SimTimePs, phase: EventPhase, event: DomainEvent) -> None:
        when = int(when_ps)
        if when < self.timeline.now():
            raise PastEventError(f"cannot schedule {event.event_id} at {when}; now={self.timeline.now()}")
        self.pump.register(event)
        key = (when, phase)
        local_sequence = self._sequences[key]
        self._sequences[key] += 1
        priority = encode_priority(phase, local_sequence)
        self.timeline.schedule(Event(when, Process(self.pump, "dispatch", [event.event_id]), priority))

    def schedule_after(self, delay_ps: DurationPs, phase: EventPhase, event: DomainEvent) -> None:
        if int(delay_ps) < 0:
            raise PastEventError("negative delay")
        self.schedule_at(SimTimePs(self.timeline.now() + int(delay_ps)), phase, event)

    def run(self) -> None:
        if not self._initialized:
            self.timeline.init()
            self._initialized = True
        self.timeline.run()

    @property
    def pending_count(self) -> int:
        return len(self.pump.registry)

    @property
    def dispatched(self) -> int:
        return self.timeline.run_counter
