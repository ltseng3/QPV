"""Stable persistence records."""

from __future__ import annotations

from dataclasses import asdict

from qorchsim.qpv.models import RoundResult


def round_record(result: RoundResult) -> dict[str, object]:
    value = asdict(result)
    value["reason_codes"] = "|".join(result.reason_codes)
    value["attack_ids"] = "|".join(result.attack_ids)
    return value
