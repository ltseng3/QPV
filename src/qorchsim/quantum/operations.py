"""Portable density-matrix quantum operations."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from qorchsim.quantum.kraus import apply_to_subsystem, depolarizing, validate_density_matrix
from qorchsim.quantum.states import QuantumHandle, QuantumPairHandle, QuantumStateStore

ComplexMatrix = NDArray[np.complex128]
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
I2 = np.eye(2, dtype=complex)
PHI_PLUS = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
PHI_PLUS_RHO = np.outer(PHI_PLUS, PHI_PLUS.conj())


class QuantumOperations(Protocol):
    """Quantum execution port used by device and protocol logic."""

    def create_epr_pair(self, pair_id: str, fidelity: float = 1.0) -> QuantumPairHandle: ...
    def prepare_bb84(self, qubit_id: str, state_id: str, basis: int, bit: int) -> QuantumHandle: ...
    def measure_bb84(self, qubit: QuantumHandle, basis: int, rng: Generator) -> int: ...
    def apply_kraus(self, qubit: QuantumHandle, operators: list[ComplexMatrix]) -> None: ...
    def fidelity_to_bell_phi_plus(self, pair: QuantumPairHandle) -> float: ...


class DensityMatrixQuantumOperations:
    """Small exact density-matrix backend for QPV-sized states.

    The backend is intentionally simulator-independent. A SeQUeNCe implementation can
    replace it behind the same port when the external package is installed.
    """

    def __init__(self, store: QuantumStateStore | None = None) -> None:
        self.store = store or QuantumStateStore()

    def create_epr_pair(self, pair_id: str, fidelity: float = 1.0) -> QuantumPairHandle:
        fidelity = float(np.clip(fidelity, 0.25, 1.0))
        if fidelity == 1.0:
            rho = PHI_PLUS_RHO.copy()
        else:
            # Werner state with exact Bell-state fidelity F.
            rho = fidelity * PHI_PLUS_RHO + (1.0 - fidelity) / 3.0 * (
                np.eye(4, dtype=complex) - PHI_PLUS_RHO
            )
        handles = self.store.put(pair_id, [f"{pair_id}:0", f"{pair_id}:1"], rho)
        return QuantumPairHandle(handles[0], handles[1])

    def prepare_bb84(self, qubit_id: str, state_id: str, basis: int, bit: int) -> QuantumHandle:
        return self.store.clone_single_from_bit(state_id, qubit_id, basis, bit)

    def _apply_unitary(self, handle: QuantumHandle, operator: ComplexMatrix) -> None:
        state = self.store.state(handle)
        qubits = len(state.qubit_ids)
        expanded = np.array([[1]], dtype=complex)
        for index in range(qubits):
            expanded = np.kron(expanded, operator if index == handle.index else I2)
        state.rho = expanded @ state.rho @ expanded.conj().T
        validate_density_matrix(state.rho)

    def measure_bb84(self, qubit: QuantumHandle, basis: int, rng: Generator) -> int:
        if basis not in (0, 1):
            raise ValueError("BB84 basis must be 0 or 1")
        if basis == 1:
            self._apply_unitary(qubit, H)
        state = self.store.state(qubit)
        qubits = len(state.qubit_ids)
        projectors = [np.diag([1, 0]).astype(complex), np.diag([0, 1]).astype(complex)]
        expanded = []
        probabilities = []
        for projector in projectors:
            op = np.array([[1]], dtype=complex)
            for index in range(qubits):
                op = np.kron(op, projector if index == qubit.index else I2)
            expanded.append(op)
            probabilities.append(max(0.0, float(np.real(np.trace(op @ state.rho)))))
        total = sum(probabilities)
        if total <= 0:
            raise ValueError("measurement probabilities sum to zero")
        probabilities = [value / total for value in probabilities]
        outcome = int(rng.choice([0, 1], p=probabilities))
        op = expanded[outcome]
        state.rho = op @ state.rho @ op.conj().T / probabilities[outcome]
        validate_density_matrix(state.rho)
        return outcome

    def apply_kraus(self, qubit: QuantumHandle, operators: list[ComplexMatrix]) -> None:
        state = self.store.state(qubit)
        state.rho = apply_to_subsystem(
            state.rho,
            operators,
            qubit.index,
            len(state.qubit_ids),
        )

    def apply_depolarizing(self, qubit: QuantumHandle, probability: float) -> None:
        self.apply_kraus(qubit, depolarizing(probability))

    def fidelity_to_bell_phi_plus(self, pair: QuantumPairHandle) -> float:
        rho = self.store.state(pair.first).rho
        return float(np.real(PHI_PLUS.conj().T @ rho @ PHI_PLUS))
