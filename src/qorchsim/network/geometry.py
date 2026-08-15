"""Geometry and causal/timing calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """Cartesian position in metres."""

    x_m: float
    y_m: float = 0.0


def distance(a: Position, b: Position) -> float:
    """Euclidean distance in metres."""
    return math.hypot(a.x_m - b.x_m, a.y_m - b.y_m)


def propagation_delay_ps(a: Position, b: Position, speed_m_s: float) -> int:
    """Causal propagation delay, rounded upward to picoseconds."""
    if speed_m_s <= 0:
        raise ValueError("propagation speed must be positive")
    return int(math.ceil(distance(a, b) / speed_m_s * 1e12))


def causal_margin_m(a: Position, t_a_ps: int, b: Position, t_b_ps: int, c_m_s: float = 299_792_458.0) -> float:
    """Positive for spacelike separation, negative for causal connectivity."""
    return distance(a, b) - c_m_s * abs(t_b_ps - t_a_ps) / 1e12


def delay_to_distance_m(delta_ps: int, speed_m_s: float) -> float:
    """Round-trip timing-window change converted to one-way distance tolerance."""
    return speed_m_s * delta_ps / 1e12 / 2.0
