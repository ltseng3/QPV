"""Verifier timestamp-forgery attack."""

from __future__ import annotations

from dataclasses import replace

from qorchsim.attacks.base import AttackContext, IdentityAttack
from qorchsim.qpv.models import VerifierReport


class TimestampForgeryAttack(IdentityAttack):
    """Bias reported timestamps while preserving physical and local observations."""

    def __init__(self, attack_id: str, node_id: str, bias_ps: int, fields: tuple[str, ...]) -> None:
        self.attack_id = attack_id
        self.node_id = node_id
        self.bias_ps = bias_ps
        self.fields = fields

    def alter_report(self, report: object, ctx: AttackContext) -> object:
        if not isinstance(report, VerifierReport) or report.verifier_id != self.node_id:
            return report
        updates: dict[str, object] = {"attack_ids": (*report.attack_ids, self.attack_id)}
        if "commitment_arrival" in self.fields and report.commitment_reported_ps is not None:
            updates["commitment_reported_ps"] = report.commitment_reported_ps + self.bias_ps
        if "answer_arrival" in self.fields and report.answer_reported_ps is not None:
            updates["answer_reported_ps"] = report.answer_reported_ps + self.bias_ps
        return replace(report, **updates)
