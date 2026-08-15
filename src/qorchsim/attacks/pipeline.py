"""Ordered attack pipeline."""

from __future__ import annotations

from qorchsim.attacks.base import AttackContext, AttackModel, QuantumSendDecision
from qorchsim.cloudsim.resources import ResourceSnapshot
from qorchsim.network.transmissions import ClassicalTransmission, QuantumTransmission


class AttackPipeline:
    """Apply attacks in user-specified order."""

    def __init__(self, attacks: list[AttackModel] | None = None) -> None:
        self.attacks = list(attacks or [])

    @property
    def attack_ids(self) -> tuple[str, ...]:
        return tuple(attack.attack_id for attack in self.attacks)

    def alter_inventory(self, snapshot: ResourceSnapshot, ctx: AttackContext) -> ResourceSnapshot:
        result = snapshot
        for attack in self.attacks:
            result = attack.alter_inventory(result, ctx)
        return result

    def alter_plan(self, plan: object, ctx: AttackContext) -> object:
        result = plan
        for attack in self.attacks:
            result = attack.alter_plan(result, ctx)
        return result

    def alter_classical(self, tx: ClassicalTransmission, ctx: AttackContext) -> tuple[ClassicalTransmission, ...]:
        transmissions = (tx,)
        for attack in self.attacks:
            transmissions = tuple(
                output
                for candidate in transmissions
                for output in attack.alter_classical(candidate, ctx)
            )
        return transmissions

    def decide_quantum_send(self, tx: QuantumTransmission, ctx: AttackContext) -> QuantumSendDecision:
        current = QuantumSendDecision(tx, True)
        for attack in self.attacks:
            if not current.allow:
                break
            current = attack.decide_quantum_send(current.transmission, ctx)
        return current

    def alter_report(self, report: object, ctx: AttackContext) -> object:
        result = report
        for attack in self.attacks:
            result = attack.alter_report(result, ctx)
        return result

    def alter_result(self, result: object, ctx: AttackContext) -> object:
        current = result
        for attack in self.attacks:
            current = attack.alter_result(current, ctx)
        return current
