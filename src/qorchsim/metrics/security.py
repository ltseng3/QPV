"""Security metrics from round results."""

from __future__ import annotations

from qorchsim.metrics.aggregation import wilson_interval
from qorchsim.qpv.models import SessionResult


def security_summary(result: SessionResult, maximum_authenticated_radius_m: float) -> dict[str, object]:
    rounds = result.rounds
    accepted = sum(round_result.accepted for round_result in rounds)
    outside = [r for r in rounds if abs(r.prover_position_m) > maximum_authenticated_radius_m]
    false_accepts = sum(r.accepted for r in outside)
    far = false_accepts / len(outside) if outside else 0.0
    low, high = wilson_interval(false_accepts, len(outside))
    return {
        "session_accepted": result.accepted,
        "rounds": len(rounds),
        "accepted_rounds": accepted,
        "committed_rounds": result.committed_rounds,
        "valid_committed_rounds": result.valid_committed_rounds,
        "qber": result.qber,
        "timing_violations": result.timing_violations,
        "false_accept_rate": far,
        "false_accept_wilson_95": [low, high],
        "reason_codes": list(result.reason_codes),
    }
