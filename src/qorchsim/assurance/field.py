"""Spatial-assurance field evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from qorchsim.assurance.models import AssuranceDeployment, VerifierTimingModel
from qorchsim.network.geometry import Position, distance


def timing_margin_ps(
    deployment: AssuranceDeployment,
    verifier: VerifierTimingModel,
    position: Position,
) -> float:
    """Return the residual timing margin m_i(p) in picoseconds."""
    propagation_ps = (
        2.0
        * distance(position, verifier.position)
        / deployment.propagation_speed_m_s
        * 1e12
    )
    return verifier.deadline_ps - verifier.deterministic_offset_ps - propagation_ps


def local_assurance(
    deployment: AssuranceDeployment,
    verifier: VerifierTimingModel,
    position: Position,
) -> float:
    """Return the honest timing-pass probability for one verifier."""
    probability = verifier.error_model.cdf(timing_margin_ps(deployment, verifier, position))
    return min(1.0, max(0.0, float(probability)))


def joint_assurance(deployment: AssuranceDeployment, position: Position) -> float:
    """Return product-form assurance under independent verifier timing errors."""
    log_probability = 0.0
    for verifier in deployment.verifiers:
        probability = local_assurance(deployment, verifier, position)
        if probability <= 0.0:
            return 0.0
        log_probability += math.log(probability)
    return math.exp(log_probability)


def assurance_grid(
    deployment: AssuranceDeployment,
    x_m: Sequence[float] | np.ndarray,
    y_m: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Evaluate A(p) on a Cartesian grid with shape (len(y_m), len(x_m))."""
    xs = np.asarray(x_m, dtype=float)
    ys = np.asarray(y_m, dtype=float)
    if xs.ndim != 1 or ys.ndim != 1 or len(xs) == 0 or len(ys) == 0:
        raise ValueError("x_m and y_m must be non-empty one-dimensional arrays")
    values = np.empty((len(ys), len(xs)), dtype=float)
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            values[row, column] = joint_assurance(deployment, Position(float(x), float(y)))
    return values
