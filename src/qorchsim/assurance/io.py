"""YAML loading for standalone spatial-assurance studies."""

from __future__ import annotations

from pathlib import Path

import yaml

from qorchsim.assurance.models import AssuranceDeployment, GaussianTimingError, VerifierTimingModel
from qorchsim.network.geometry import Position


def _duration_ps(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    units = {"ps": 1.0, "ns": 1e3, "us": 1e6, "µs": 1e6, "ms": 1e9, "s": 1e12}
    for suffix, factor in units.items():
        if text.endswith(suffix):
            return float(text[: -len(suffix)].strip()) * factor
    raise ValueError(f"unsupported duration {value!r}")


def load_assurance_deployment(path: str | Path) -> AssuranceDeployment:
    """Load the compact paper-study YAML schema."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    verifiers = []
    for item in raw["verifiers"]:
        error = item["error"]
        if error["type"] != "gaussian":
            raise ValueError("paper YAML currently supports gaussian errors only")
        verifiers.append(
            VerifierTimingModel(
                verifier_id=item["id"],
                position=Position(float(item["x_m"]), float(item.get("y_m", 0.0))),
                deadline_ps=_duration_ps(item["deadline"]),
                deterministic_offset_ps=_duration_ps(item.get("deterministic_offset", 0)),
                error_model=GaussianTimingError(
                    stddev_ps=_duration_ps(error["stddev"]),
                    mean_ps=_duration_ps(error.get("mean", 0)),
                ),
            )
        )
    return AssuranceDeployment(
        tuple(verifiers),
        propagation_speed_m_s=float(raw.get("propagation_speed_m_s", 299_792_458.0)),
    )
