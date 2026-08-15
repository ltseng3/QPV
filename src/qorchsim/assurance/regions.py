"""Region masks and operational metrics derived from assurance grids."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np

from qorchsim.assurance.models import AssuranceDeployment
from qorchsim.network.geometry import Position, distance


@dataclass(frozen=True, slots=True)
class RegionMetrics:
    """Grid-estimated operational metrics for a fixed assurance level."""

    gamma: float
    area_m2: float
    worst_case_radius_m: float | None
    max_assurance: float
    max_position: Position
    reference_assurance: float


def deterministic_grid(
    deployment: AssuranceDeployment,
    x_m: Sequence[float] | np.ndarray,
    y_m: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Return the deterministic timing-feasible mask on a Cartesian grid."""
    xs = np.asarray(x_m, dtype=float)
    ys = np.asarray(y_m, dtype=float)
    mask = np.ones((len(ys), len(xs)), dtype=bool)
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            p = Position(float(x), float(y))
            for verifier in deployment.verifiers:
                propagation_ps = (
                    2.0
                    * distance(p, verifier.position)
                    / deployment.propagation_speed_m_s
                    * 1e12
                )
                if propagation_ps + verifier.deterministic_offset_ps > verifier.deadline_ps:
                    mask[row, column] = False
                    break
    return mask


def region_metrics(
    assurance: np.ndarray,
    x_m: Sequence[float] | np.ndarray,
    y_m: Sequence[float] | np.ndarray,
    gamma: float,
    reference: Position = Position(0.0, 0.0),
) -> RegionMetrics:
    """Compute area, extent, maximum assurance, and reference assurance from a grid."""
    if not 0.0 < gamma < 1.0:
        raise ValueError("gamma must lie in (0, 1)")
    xs = np.asarray(x_m, dtype=float)
    ys = np.asarray(y_m, dtype=float)
    values = np.asarray(assurance, dtype=float)
    if values.shape != (len(ys), len(xs)):
        raise ValueError("assurance shape must be (len(y_m), len(x_m))")
    if len(xs) < 2 or len(ys) < 2:
        raise ValueError("at least two samples per axis are required")

    dx = float(np.mean(np.diff(xs)))
    dy = float(np.mean(np.diff(ys)))
    mask = values >= gamma
    area = float(mask.sum()) * abs(dx * dy)

    max_flat = int(np.nanargmax(values))
    max_row, max_column = np.unravel_index(max_flat, values.shape)
    max_position = Position(float(xs[max_column]), float(ys[max_row]))
    max_assurance = float(values[max_row, max_column])

    ref_column = int(np.argmin(np.abs(xs - reference.x_m)))
    ref_row = int(np.argmin(np.abs(ys - reference.y_m)))
    reference_assurance = float(values[ref_row, ref_column])

    if mask.any():
        rows, columns = np.nonzero(mask)
        radii = np.hypot(xs[columns] - reference.x_m, ys[rows] - reference.y_m)
        worst_case_radius = float(radii.max())
    else:
        worst_case_radius = None

    return RegionMetrics(
        gamma=gamma,
        area_m2=area,
        worst_case_radius_m=worst_case_radius,
        max_assurance=max_assurance,
        max_position=max_position,
        reference_assurance=reference_assurance,
    )
