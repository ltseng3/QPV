"""Kraus-channel construction and subsystem application."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from qorchsim.errors import QuantumStateValidationError

ComplexMatrix = NDArray[np.complex128]
I2 = np.eye(2, dtype=complex)


def amplitude_damping(gamma: float) -> list[ComplexMatrix]:
    """Return amplitude-damping Kraus operators."""
    gamma = float(np.clip(gamma, 0.0, 1.0))
    return [
        np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=complex),
        np.array([[0, np.sqrt(gamma)], [0, 0]], dtype=complex),
    ]


def phase_damping_from_coherence(coherence: float) -> list[ComplexMatrix]:
    """Return a dephasing channel with off-diagonal multiplier ``coherence``."""
    coherence = float(np.clip(coherence, 0.0, 1.0))
    probability_z = (1.0 - coherence) / 2.0
    return [np.sqrt(1 - probability_z) * I2, np.sqrt(probability_z) * np.diag([1, -1])]


def depolarizing(probability: float) -> list[ComplexMatrix]:
    """Return single-qubit depolarizing Kraus operators."""
    p = float(np.clip(probability, 0.0, 1.0))
    x = np.array([[0, 1], [1, 0]], dtype=complex)
    y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    z = np.array([[1, 0], [0, -1]], dtype=complex)
    return [np.sqrt(1 - p) * I2, *(np.sqrt(p / 3) * op for op in (x, y, z))]


def _expand(operator: ComplexMatrix, target: int, qubits: int) -> ComplexMatrix:
    result = np.array([[1]], dtype=complex)
    for index in range(qubits):
        result = np.kron(result, operator if index == target else I2)
    return result


def apply_to_subsystem(
    rho: ComplexMatrix,
    operators: list[ComplexMatrix],
    target: int,
    qubits: int,
    *,
    validate: bool = True,
) -> ComplexMatrix:
    """Apply a one-qubit Kraus channel to a subsystem."""
    transformed = np.zeros_like(rho, dtype=complex)
    for operator in operators:
        expanded = _expand(operator, target, qubits)
        transformed += expanded @ rho @ expanded.conj().T
    if validate:
        validate_density_matrix(transformed)
    return transformed


def validate_density_matrix(rho: ComplexMatrix, tolerance: float = 1e-8) -> None:
    """Validate Hermiticity, unit trace and positive semidefiniteness."""
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise QuantumStateValidationError("density matrix must be square")
    if not np.allclose(rho, rho.conj().T, atol=tolerance):
        raise QuantumStateValidationError("density matrix is not Hermitian")
    if not np.isclose(np.trace(rho), 1.0, atol=tolerance):
        raise QuantumStateValidationError(f"density matrix trace is {np.trace(rho)}")
    eigenvalues = np.linalg.eigvalsh(rho)
    if float(np.min(eigenvalues)) < -tolerance:
        raise QuantumStateValidationError(f"negative eigenvalue {float(np.min(eigenvalues))}")
