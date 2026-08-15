import math
from statistics import NormalDist

import numpy as np

from qorchsim.assurance.field import assurance_grid, joint_assurance, local_assurance
from qorchsim.assurance.models import (
    AssuranceDeployment,
    EmpiricalTimingError,
    GaussianTimingError,
    VerifierTimingModel,
)
from qorchsim.assurance.regions import deterministic_grid
from qorchsim.assurance.repetition import hoeffding_round_count, session_assurance
from qorchsim.network.geometry import Position


C = 299_792_458.0


def verifier(x: float, y: float, radius_m: float = 101.0, sigma_ns: float = 1.0):
    return VerifierTimingModel(
        verifier_id=f"v-{x}-{y}",
        position=Position(x, y),
        deadline_ps=(2 * radius_m / C) * 1e12,
        deterministic_offset_ps=0,
        error_model=GaussianTimingError(sigma_ns * 1000),
    )


def test_gaussian_cdf_matches_standard_normal() -> None:
    model = GaussianTimingError(1000)
    assert math.isclose(model.cdf(0), 0.5, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(model.cdf(1000), NormalDist().cdf(1), rel_tol=0, abs_tol=1e-12)
    assert math.isclose(model.cdf(-1000), NormalDist().cdf(-1), rel_tol=0, abs_tol=1e-12)


def test_empirical_cdf() -> None:
    model = EmpiricalTimingError((3, -1, 1, 1))
    assert model.cdf(-2) == 0
    assert model.cdf(1) == 0.75
    assert model.cdf(3) == 1


def test_nominal_radius_is_local_half_assurance() -> None:
    v = verifier(0, 0, radius_m=100)
    deployment = AssuranceDeployment((v,), C)
    assert math.isclose(local_assurance(deployment, v, Position(100, 0)), 0.5, abs_tol=1e-12)


def test_local_alpha_contour_identity() -> None:
    alpha = 0.99
    sigma_ps = 1000.0
    radius = 100.0
    z = NormalDist().inv_cdf(alpha)
    alpha_radius = radius - C * (sigma_ps * z / 1e12) / 2
    v = verifier(0, 0, radius_m=radius, sigma_ns=1)
    deployment = AssuranceDeployment((v,), C)
    got = local_assurance(deployment, v, Position(alpha_radius, 0))
    assert math.isclose(got, alpha, rel_tol=0, abs_tol=1e-10)


def test_joint_assurance_is_product() -> None:
    a = verifier(-100, 0)
    b = verifier(100, 0)
    deployment = AssuranceDeployment((a, b), C)
    p = Position(0.2, 0)
    expected = local_assurance(deployment, a, p) * local_assurance(deployment, b, p)
    assert math.isclose(joint_assurance(deployment, p), expected, rel_tol=1e-12)


def test_assurance_regions_are_nested_on_grid() -> None:
    deployment = AssuranceDeployment(
        (verifier(100, 0), verifier(-100, 0), verifier(0, 100), verifier(0, -100)),
        C,
    )
    axis = np.linspace(-2, 2, 81)
    values = assurance_grid(deployment, axis, axis)
    assert np.all((values >= 0.999) <= (values >= 0.99))
    assert np.all((values >= 0.99) <= (values >= 0.90))


def test_symmetric_deployment_is_symmetric() -> None:
    deployment = AssuranceDeployment(
        (verifier(100, 0), verifier(-100, 0), verifier(0, 100), verifier(0, -100)),
        C,
    )
    for x, y in ((0.3, 0.7), (0.9, -0.2), (1.2, 1.1)):
        values = [
            joint_assurance(deployment, Position(x, y)),
            joint_assurance(deployment, Position(-x, y)),
            joint_assurance(deployment, Position(x, -y)),
            joint_assurance(deployment, Position(-x, -y)),
        ]
        assert max(values) - min(values) < 1e-12


def test_deterministic_limit_agrees_away_from_boundary() -> None:
    v = verifier(0, 0, radius_m=100, sigma_ns=1e-6)
    deployment = AssuranceDeployment((v,), C)
    assert joint_assurance(deployment, Position(99, 0)) > 1 - 1e-12
    assert joint_assurance(deployment, Position(101, 0)) < 1e-12


def test_repetition_and_hoeffding() -> None:
    assert math.isclose(session_assurance(0.5, 2, 1), 0.75)
    assert session_assurance(0.95, 100, 90) > session_assurance(0.85, 100, 90)
    assert hoeffding_round_count(0.01, 0.1) == math.ceil(math.log(100) / 0.02)
