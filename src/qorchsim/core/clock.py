"""Simulation time conversion and clock protocols."""

from __future__ import annotations

import math
from typing import Protocol

from qorchsim.types import DurationPs, SimTimePs

PS_PER_SECOND = 1_000_000_000_000


def seconds_to_ps(value: float) -> DurationPs:
    """Round a measured/configured duration to the nearest picosecond."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("duration seconds must be finite and nonnegative")
    return DurationPs(int(round(value * PS_PER_SECOND)))


def causal_seconds_to_ps(value: float) -> DurationPs:
    """Round upward so a physical arrival is never scheduled too early."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("duration seconds must be finite and nonnegative")
    return DurationPs(int(math.ceil(value * PS_PER_SECOND)))


def ps_to_seconds(value: int) -> float:
    """Convert picoseconds to seconds."""
    return value / PS_PER_SECOND


class SimulationClock(Protocol):
    """Read-only simulation clock port."""

    def now_ps(self) -> SimTimePs:
        """Return current physical simulation time."""
