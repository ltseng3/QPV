"""Round and session acceptance policies."""

from __future__ import annotations

from dataclasses import dataclass

from qorchsim.qpv.models import PolicyDecision, RoundResult, SessionResult, VerifierReport
from qorchsim.qpv.plans import RoundPlan
from qorchsim.policies.freshness import validate_freshness


@dataclass(frozen=True, slots=True)
class AcceptanceThresholds:
    minimum_committed_rounds: int
    maximum_qber: float
    maximum_timing_violations: int
    clock_uncertainty_ps: int = 0


class BaselineRoundAcceptance:
    """Trust reported timestamps and require matching measurements."""

    def decide(self, plan: RoundPlan, reports: tuple[VerifierReport, ...]) -> PolicyDecision:
        reasons: list[str] = []
        if len(reports) < 2:
            reasons.append("missing_verifier_report")
            return PolicyDecision(False, tuple(reasons))
        for report in reports:
            if report.commitment != 1:
                reasons.append(f"no_commitment:{report.verifier_id}")
            if report.answer_reported_ps is None or report.answer_reported_ps > report.answer_deadline_ps:
                reasons.append(f"reported_answer_deadline:{report.verifier_id}")
            if report.local_measurement is not None and report.answer is not None and report.local_measurement != report.answer:
                reasons.append(f"outcome_mismatch:{report.verifier_id}")
        return PolicyDecision(not reasons, tuple(reasons))


class SecurityAwareRoundAcceptance(BaselineRoundAcceptance):
    """Add freshness and physical/reported consistency checks."""

    def __init__(self, clock_uncertainty_ps: int) -> None:
        self.clock_uncertainty_ps = clock_uncertainty_ps

    def decide(self, plan: RoundPlan, reports: tuple[VerifierReport, ...]) -> PolicyDecision:
        base = super().decide(plan, reports)
        reasons = list(base.reason_codes)
        for report in reports:
            freshness = validate_freshness(
                expected_nonce=plan.nonce,
                actual_nonce=report.nonce,
                expected_epoch=plan.telemetry_epoch,
                actual_epoch=report.telemetry_epoch,
                authentic=report.authentic,
            )
            reasons.extend(f"{reason}:{report.verifier_id}" for reason in freshness.reason_codes)
            if report.answer_physical_ps is not None and report.answer_reported_ps is not None:
                if abs(report.answer_physical_ps - report.answer_reported_ps) > self.clock_uncertainty_ps:
                    reasons.append(f"timestamp_inconsistency:{report.verifier_id}")
            if report.commitment_physical_ps is not None and report.commitment_reported_ps is not None:
                if abs(report.commitment_physical_ps - report.commitment_reported_ps) > self.clock_uncertainty_ps:
                    reasons.append(f"commitment_timestamp_inconsistency:{report.verifier_id}")
        return PolicyDecision(not reasons, tuple(dict.fromkeys(reasons)))


def aggregate_session(
    session_id: str,
    rounds: tuple[RoundResult, ...],
    thresholds: AcceptanceThresholds,
) -> SessionResult:
    committed = sum(result.committed for result in rounds)
    valid = sum(result.valid_state_commitment for result in rounds)
    compared = [result for result in rounds if result.measurement_match is not None]
    mismatches = sum(result.measurement_match is False for result in compared)
    qber = mismatches / len(compared) if compared else 1.0
    timing = sum(
        margin is not None and margin < 0
        for result in rounds
        for margin in (
            result.commitment_physical_margin_ps,
            result.v0_response_physical_margin_ps,
            result.v1_response_physical_margin_ps,
        )
    )
    reasons: list[str] = []
    if committed < thresholds.minimum_committed_rounds:
        reasons.append("insufficient_committed_rounds")
    if qber > thresholds.maximum_qber:
        reasons.append("qber_exceeded")
    if timing > thresholds.maximum_timing_violations:
        reasons.append("timing_violations_exceeded")
    return SessionResult(
        session_id=session_id,
        rounds=rounds,
        accepted=not reasons,
        committed_rounds=committed,
        valid_committed_rounds=valid,
        outcome_mismatches=mismatches,
        timing_violations=timing,
        qber=qber,
        reason_codes=tuple(reasons),
    )
