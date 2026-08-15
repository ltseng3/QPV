"""Repeated-round timing-assurance utilities."""

from __future__ import annotations

import math


def session_assurance(single_round_assurance: float, rounds: int, minimum_successes: int) -> float:
    """Return P[Binomial(rounds, p) >= minimum_successes] exactly."""
    p = float(single_round_assurance)
    if not 0.0 <= p <= 1.0:
        raise ValueError("single_round_assurance must lie in [0, 1]")
    if rounds < 1:
        raise ValueError("rounds must be at least 1")
    if not 0 <= minimum_successes <= rounds:
        raise ValueError("minimum_successes must lie in [0, rounds]")
    if minimum_successes == 0:
        return 1.0
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0

    # Direct summation is stable for the moderate N used in the paper studies.
    return math.fsum(
        math.comb(rounds, k) * (p**k) * ((1.0 - p) ** (rounds - k))
        for k in range(minimum_successes, rounds + 1)
    )


def hoeffding_round_count(error_probability: float, assurance_gap: float) -> int:
    """Return ceil(log(1/delta)/(2 eta^2)) from the paper's Hoeffding bound."""
    if not 0.0 < error_probability < 1.0:
        raise ValueError("error_probability must lie in (0, 1)")
    if assurance_gap <= 0.0:
        raise ValueError("assurance_gap must be positive")
    return math.ceil(math.log(1.0 / error_probability) / (2.0 * assurance_gap**2))
