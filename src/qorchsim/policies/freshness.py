"""Freshness validation."""

from __future__ import annotations

from qorchsim.qpv.models import PolicyDecision


def validate_freshness(
    *,
    expected_nonce: str,
    actual_nonce: str,
    expected_epoch: int,
    actual_epoch: int,
    authentic: bool,
) -> PolicyDecision:
    reasons: list[str] = []
    if not authentic:
        reasons.append("unauthenticated")
    if actual_nonce != expected_nonce:
        reasons.append("nonce_mismatch")
    if actual_epoch != expected_epoch:
        reasons.append("telemetry_epoch_mismatch")
    return PolicyDecision(not reasons, tuple(reasons))
