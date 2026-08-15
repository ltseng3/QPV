"""Immutable transmission envelopes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from qorchsim.quantum.states import QuantumHandle


@dataclass(frozen=True, slots=True)
class ClassicalTransmission:
    transmission_id: str
    link_id: str
    source: str
    destination: str
    message_type: str
    payload: Any
    send_time_ps: int
    propagation_delay_ps: int
    added_delay_ps: int = 0
    dropped: bool = False
    attack_ids: tuple[str, ...] = ()

    @property
    def arrival_time_ps(self) -> int:
        return self.send_time_ps + self.propagation_delay_ps + self.added_delay_ps

    def with_attack(self, attack_id: str, **changes: Any) -> "ClassicalTransmission":
        return replace(self, attack_ids=(*self.attack_ids, attack_id), **changes)


@dataclass(frozen=True, slots=True)
class QuantumTransmission:
    transmission_id: str
    link_id: str
    source: str
    destination: str
    qubit: QuantumHandle
    send_time_ps: int
    propagation_delay_ps: int
    survival_probability: float
    added_delay_ps: int = 0
    dropped: bool = False
    attack_ids: tuple[str, ...] = ()

    @property
    def arrival_time_ps(self) -> int:
        return self.send_time_ps + self.propagation_delay_ps + self.added_delay_ps
