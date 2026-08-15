"""Round-plan schedule policy."""

from __future__ import annotations

from dataclasses import dataclass

from qorchsim.qpv.models import PolicyDecision
from qorchsim.qpv.plans import RoundPlan


@dataclass(frozen=True, slots=True)
class ScheduleBounds:
    minimum_delta_ps: int
    maximum_delta_ps: int
    maximum_basis_skew_ps: int


class SchedulePolicy:
    """Validate challenge-to-basis delay and bilateral skew."""

    def __init__(self, bounds: ScheduleBounds) -> None:
        self.bounds = bounds

    def validate(self, plan: RoundPlan) -> PolicyDecision:
        delta_x = plan.x_send_ps - plan.challenge_send_ps
        delta_y = plan.y_send_ps - plan.challenge_send_ps
        reasons: list[str] = []
        if not self.bounds.minimum_delta_ps <= delta_x <= self.bounds.maximum_delta_ps:
            reasons.append("x_delta_out_of_bounds")
        if not self.bounds.minimum_delta_ps <= delta_y <= self.bounds.maximum_delta_ps:
            reasons.append("y_delta_out_of_bounds")
        if abs(plan.x_send_ps - plan.y_send_ps) > self.bounds.maximum_basis_skew_ps:
            reasons.append("basis_skew_out_of_bounds")
        return PolicyDecision(not reasons, tuple(reasons))
