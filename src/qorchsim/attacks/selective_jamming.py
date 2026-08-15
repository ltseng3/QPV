"""Selective link-level jamming represented as delay or loss."""

from __future__ import annotations

from dataclasses import replace

from qorchsim.attacks.base import AttackContext, IdentityAttack, QuantumSendDecision
from qorchsim.network.transmissions import ClassicalTransmission, QuantumTransmission


class SelectiveJammingAttack(IdentityAttack):
    """Filter by link/message/time and probabilistically drop or delay traffic."""

    def __init__(
        self,
        attack_id: str,
        *,
        link_ids: tuple[str, ...] = (),
        message_types: tuple[str, ...] = (),
        start_ps: int = 0,
        end_ps: int | None = None,
        drop_probability: float = 0.0,
        added_delay_ps: int = 0,
        quantum: bool = False,
    ) -> None:
        self.attack_id = attack_id
        self.link_ids = set(link_ids)
        self.message_types = set(message_types)
        self.start_ps = start_ps
        self.end_ps = end_ps
        self.drop_probability = drop_probability
        self.added_delay_ps = added_delay_ps
        self.quantum = quantum

    def _active(self, link_id: str, message_type: str | None, now_ps: int) -> bool:
        return (
            (not self.link_ids or link_id in self.link_ids)
            and (not self.message_types or message_type in self.message_types)
            and now_ps >= self.start_ps
            and (self.end_ps is None or now_ps <= self.end_ps)
        )

    def alter_classical(self, tx: ClassicalTransmission, ctx: AttackContext) -> tuple[ClassicalTransmission, ...]:
        if not self._active(tx.link_id, tx.message_type, ctx.now_ps):
            return (tx,)
        dropped = ctx.rng.random() < self.drop_probability
        return (
            tx.with_attack(
                self.attack_id,
                dropped=dropped,
                added_delay_ps=tx.added_delay_ps + self.added_delay_ps,
            ),
        )

    def decide_quantum_send(self, tx: QuantumTransmission, ctx: AttackContext) -> QuantumSendDecision:
        if not self.quantum or not self._active(tx.link_id, None, ctx.now_ps):
            return QuantumSendDecision(tx, True)
        dropped = ctx.rng.random() < self.drop_probability
        modified = replace(
            tx,
            dropped=dropped,
            added_delay_ps=tx.added_delay_ps + self.added_delay_ps,
            attack_ids=(*tx.attack_ids, self.attack_id),
        )
        return QuantumSendDecision(modified, not dropped)
