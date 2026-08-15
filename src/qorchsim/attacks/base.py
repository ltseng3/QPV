"""Attack interfaces and context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from numpy.random import Generator

from qorchsim.cloudsim.resources import ResourceSnapshot
from qorchsim.network.transmissions import ClassicalTransmission, QuantumTransmission


@dataclass(frozen=True, slots=True)
class AttackContext:
    """Context visible to an attack at one hook."""

    now_ps: int
    session_id: str
    round_id: str | None
    rng: Generator


@dataclass(frozen=True, slots=True)
class QuantumSendDecision:
    """Decision produced at the quantum-send hook."""

    transmission: QuantumTransmission
    allow: bool = True


class AttackModel(Protocol):
    """Composable attack model. Base implementations are identity transforms."""

    attack_id: str

    def alter_inventory(self, snapshot: ResourceSnapshot, ctx: AttackContext) -> ResourceSnapshot: ...
    def alter_plan(self, plan: object, ctx: AttackContext) -> object: ...
    def alter_classical(self, tx: ClassicalTransmission, ctx: AttackContext) -> tuple[ClassicalTransmission, ...]: ...
    def decide_quantum_send(self, tx: QuantumTransmission, ctx: AttackContext) -> QuantumSendDecision: ...
    def alter_report(self, report: object, ctx: AttackContext) -> object: ...
    def alter_result(self, result: object, ctx: AttackContext) -> object: ...


class IdentityAttack:
    """Convenience base class whose hooks do nothing."""

    attack_id = "identity"

    def alter_inventory(self, snapshot: ResourceSnapshot, ctx: AttackContext) -> ResourceSnapshot:
        return snapshot

    def alter_plan(self, plan: object, ctx: AttackContext) -> object:
        return plan

    def alter_classical(self, tx: ClassicalTransmission, ctx: AttackContext) -> tuple[ClassicalTransmission, ...]:
        return (tx,)

    def decide_quantum_send(self, tx: QuantumTransmission, ctx: AttackContext) -> QuantumSendDecision:
        return QuantumSendDecision(tx, True)

    def alter_report(self, report: object, ctx: AttackContext) -> object:
        return report

    def alter_result(self, result: object, ctx: AttackContext) -> object:
        return result
