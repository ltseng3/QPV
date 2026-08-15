"""Value objects and timing-error distributions for spatial assurance."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from statistics import NormalDist
from typing import Protocol, runtime_checkable

from qorchsim.network.geometry import Position


@runtime_checkable
class TimingErrorModel(Protocol):
    """Distribution of calibrated residual timing error in picoseconds."""

    def cdf(self, error_ps: float) -> float:
        """Return P[E <= error_ps]."""


@dataclass(frozen=True, slots=True)
class GaussianTimingError:
    """Zero-mean or biased Gaussian residual timing error."""

    stddev_ps: float
    mean_ps: float = 0.0

    def __post_init__(self) -> None:
        if self.stddev_ps <= 0:
            raise ValueError("stddev_ps must be positive")

    def cdf(self, error_ps: float) -> float:
        z = (float(error_ps) - self.mean_ps) / self.stddev_ps
        return NormalDist().cdf(z)


@dataclass(frozen=True, slots=True)
class EmpiricalTimingError:
    """Empirical CDF backed by immutable calibrated timing samples."""

    samples_ps: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.samples_ps:
            raise ValueError("samples_ps must contain at least one sample")
        object.__setattr__(self, "samples_ps", tuple(sorted(float(v) for v in self.samples_ps)))

    def cdf(self, error_ps: float) -> float:
        return bisect_right(self.samples_ps, float(error_ps)) / len(self.samples_ps)


@dataclass(frozen=True, slots=True)
class VerifierTimingModel:
    """Timing and geometric parameters for one verifier."""

    verifier_id: str
    position: Position
    deadline_ps: float
    deterministic_offset_ps: float
    error_model: TimingErrorModel

    def __post_init__(self) -> None:
        if not self.verifier_id:
            raise ValueError("verifier_id must be non-empty")


@dataclass(frozen=True, slots=True)
class AssuranceDeployment:
    """Independent-verifier spatial-assurance deployment."""

    verifiers: tuple[VerifierTimingModel, ...]
    propagation_speed_m_s: float = 299_792_458.0

    def __post_init__(self) -> None:
        if not self.verifiers:
            raise ValueError("at least one verifier is required")
        if self.propagation_speed_m_s <= 0:
            raise ValueError("propagation_speed_m_s must be positive")
        ids = [item.verifier_id for item in self.verifiers]
        if len(set(ids)) != len(ids):
            raise ValueError("verifier_id values must be unique")
