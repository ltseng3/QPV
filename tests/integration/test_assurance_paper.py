from pathlib import Path

import numpy as np

from qorchsim.assurance.field import assurance_grid, joint_assurance
from qorchsim.assurance.io import load_assurance_deployment
from qorchsim.assurance.regions import region_metrics
from qorchsim.network.geometry import Position


def test_paper_configs_capture_degradation_tradeoff() -> None:
    root = Path(__file__).resolve().parents[2]
    healthy = load_assurance_deployment(root / "configs/paper/assurance_healthy.yaml")
    degraded = load_assurance_deployment(root / "configs/paper/assurance_degraded.yaml")
    removed = load_assurance_deployment(root / "configs/paper/assurance_degraded_removed.yaml")

    center = Position(0, 0)
    assert joint_assurance(healthy, center) > 0.999
    assert joint_assurance(degraded, center) < 0.99
    assert joint_assurance(removed, center) > joint_assurance(degraded, center)

    axis = np.linspace(-4, 4, 161)
    degraded_grid = assurance_grid(degraded, axis, axis)
    degraded_metric = region_metrics(degraded_grid, axis, axis, 0.99)
    assert degraded_metric.max_assurance < 0.99

    removed_grid = assurance_grid(removed, axis, axis)
    removed_metric = region_metrics(removed_grid, axis, axis, 0.99)
    assert removed_metric.area_m2 > 0
