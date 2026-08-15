"""Quantum-classical schedule-skew attack."""

from __future__ import annotations

from dataclasses import replace

from qorchsim.attacks.base import AttackContext, IdentityAttack
from qorchsim.qpv.plans import RoundPlan


class ScheduleSkewAttack(IdentityAttack):
    """Shift challenge and basis send times in the physical plan."""

    def __init__(
        self,
        attack_id: str,
        *,
        x_shift_ps: int = 0,
        y_shift_ps: int = 0,
        challenge_shift_ps: int = 0,
        modify_controller_view: bool = False,
    ) -> None:
        self.attack_id = attack_id
        self.x_shift_ps = x_shift_ps
        self.y_shift_ps = y_shift_ps
        self.challenge_shift_ps = challenge_shift_ps
        self.modify_controller_view = modify_controller_view

    def alter_plan(self, plan: object, ctx: AttackContext) -> object:
        if not isinstance(plan, RoundPlan):
            return plan
        return replace(
            plan,
            challenge_send_ps=plan.challenge_send_ps + self.challenge_shift_ps,
            x_send_ps=plan.x_send_ps + self.x_shift_ps,
            y_send_ps=plan.y_send_ps + self.y_shift_ps,
            physical_attack_ids=(*plan.physical_attack_ids, self.attack_id),
            controller_expected_original=not self.modify_controller_view,
        )
