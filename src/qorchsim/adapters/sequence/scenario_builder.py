"""Construction helpers for SeQUeNCe-backed simulations."""

from __future__ import annotations

from qorchsim.adapters.sequence.quantum_ops import SequenceQuantumOperations
from qorchsim.adapters.sequence.scheduler import SequenceEventScheduler
from qorchsim.core.event_bus import EventBus


def build_sequence_backend(stop_time_ps: int) -> tuple[EventBus, SequenceEventScheduler, SequenceQuantumOperations]:
    bus = EventBus()
    scheduler = SequenceEventScheduler(bus, stop_time_ps)
    quantum = SequenceQuantumOperations(scheduler.timeline.quantum_manager)
    return bus, scheduler, quantum
