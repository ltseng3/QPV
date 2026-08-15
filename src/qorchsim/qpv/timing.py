"""Security-relevant QPV timing metrics."""

from __future__ import annotations


def commitment_margin_ps(basis_available_ps: int | None, commitment_generated_ps: int | None) -> int | None:
    if basis_available_ps is None or commitment_generated_ps is None:
        return None
    return basis_available_ps - commitment_generated_ps


def response_margin_ps(deadline_ps: int, arrival_ps: int | None) -> int | None:
    return None if arrival_ps is None else deadline_ps - arrival_ps


def memory_margin_ps(safe_hold_ps: int | None, dwell_ps: int | None) -> int | None:
    if safe_hold_ps is None or dwell_ps is None:
        return None
    return safe_hold_ps - dwell_ps
