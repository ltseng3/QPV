"""Domain events and deterministic phases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

SEQUENCE_STRIDE = 1_000_000_000


class EventPhase(IntEnum):
    """Security-relevant event ordering at equal timestamps."""

    PHYSICAL_ARRIVAL = 0
    DEVICE_COMPLETION = 10
    PROTOCOL = 20
    CONTROL = 30
    TIMEOUT = 40
    OBSERVABILITY = 90


def encode_priority(phase: EventPhase, same_phase_sequence: int) -> int:
    """Encode phase and local sequence into a SeQUeNCe-compatible priority."""
    if same_phase_sequence < 0 or same_phase_sequence >= SEQUENCE_STRIDE:
        raise ValueError("same_phase_sequence is outside supported range")
    return int(phase) * SEQUENCE_STRIDE + same_phase_sequence


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Immutable event routed through the domain event bus."""

    event_id: str
    event_type: str
    payload: Any
