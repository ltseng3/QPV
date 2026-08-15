"""Analytical spatial-assurance models for calibrated QPV timing uncertainty."""

from qorchsim.assurance.field import (
    assurance_grid,
    joint_assurance,
    local_assurance,
    timing_margin_ps,
)
from qorchsim.assurance.models import (
    AssuranceDeployment,
    EmpiricalTimingError,
    GaussianTimingError,
    TimingErrorModel,
    VerifierTimingModel,
)
from qorchsim.assurance.regions import RegionMetrics, deterministic_grid, region_metrics
from qorchsim.assurance.repetition import hoeffding_round_count, session_assurance

__all__ = [
    "AssuranceDeployment",
    "EmpiricalTimingError",
    "GaussianTimingError",
    "RegionMetrics",
    "TimingErrorModel",
    "VerifierTimingModel",
    "assurance_grid",
    "deterministic_grid",
    "hoeffding_round_count",
    "joint_assurance",
    "local_assurance",
    "region_metrics",
    "session_assurance",
    "timing_margin_ps",
]
