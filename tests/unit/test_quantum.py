import numpy as np

from qorchsim.core.random_streams import RandomStreams
from qorchsim.quantum.kraus import amplitude_damping, apply_to_subsystem, validate_density_matrix
from qorchsim.quantum.operations import DensityMatrixQuantumOperations


def test_ideal_epr_same_basis_correlations() -> None:
    operations = DensityMatrixQuantumOperations()
    for basis in (0, 1):
        pair = operations.create_epr_pair(f"pair-{basis}")
        rng = RandomStreams(4).generator(f"basis-{basis}")
        first = operations.measure_bb84(pair.first, basis, rng)
        second = operations.measure_bb84(pair.second, basis, rng)
        assert first == second


def test_intercept_random_basis_causes_quarter_qber() -> None:
    operations = DensityMatrixQuantumOperations()
    rng = RandomStreams(99).generator("experiment")
    mismatches = 0
    trials = 2_000
    for index in range(trials):
        pair = operations.create_epr_pair(f"pair-{index}")
        attack_basis = int(rng.integers(0, 2))
        attack_bit = operations.measure_bb84(pair.second, attack_basis, rng)
        replacement = operations.prepare_bb84(f"q-{index}", f"s-{index}", attack_basis, attack_bit)
        honest_basis = int(rng.integers(0, 2))
        prover = operations.measure_bb84(replacement, honest_basis, rng)
        verifier = operations.measure_bb84(pair.first, honest_basis, rng)
        mismatches += prover != verifier
    assert 0.21 <= mismatches / trials <= 0.29


def test_kraus_channel_preserves_density_state() -> None:
    rho = np.array([[0, 0], [0, 1]], dtype=complex)
    transformed = apply_to_subsystem(rho, amplitude_damping(0.5), 0, 1)
    validate_density_matrix(transformed)
    assert np.allclose(transformed, np.diag([0.5, 0.5]))
