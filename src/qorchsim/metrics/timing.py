"""Timing distribution extraction."""

from __future__ import annotations

from qorchsim.metrics.aggregation import continuous_summary
from qorchsim.qpv.models import SessionResult


def timing_summary(result: SessionResult) -> dict[str, object]:
    return {
        "memory_dwell_ps": continuous_summary(
            r.memory_dwell_ps for r in result.rounds if r.memory_dwell_ps is not None
        ),
        "commitment_margin_ps": continuous_summary(
            r.commitment_physical_margin_ps
            for r in result.rounds
            if r.commitment_physical_margin_ps is not None
        ),
        "v0_response_margin_ps": continuous_summary(
            r.v0_response_physical_margin_ps
            for r in result.rounds
            if r.v0_response_physical_margin_ps is not None
        ),
    }
