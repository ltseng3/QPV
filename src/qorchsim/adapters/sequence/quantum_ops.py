"""Density-matrix quantum operations backed by SeQUeNCe's quantum manager.

This module is the only quantum-state adapter used by the ``sequence_qpv`` execution
model. Domain objects keep simulator-independent :class:`QuantumHandle` values;
this adapter maps those handles to SeQUeNCe quantum-manager keys.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from qorchsim.quantum.kraus import apply_to_subsystem, validate_density_matrix
from qorchsim.quantum.operations import H, I2, PHI_PLUS, PHI_PLUS_RHO
from qorchsim.quantum.states import QuantumHandle, QuantumPairHandle

ComplexMatrix = NDArray[np.complex128]


class SequenceQuantumOperations:
    """Implement the portable quantum-operations port with SeQUeNCe state storage.

    SeQUeNCe 1.0.0's density-matrix manager exposes ``new``, ``get`` and ``set``.
    QOrchSim uses those public operations as the state authority and performs the
    small, explicit subsystem transforms required by commitment QPV. This avoids
    leaking manager keys outside the adapter while preserving exact composite-state
    evolution and manager ownership of entangled states.
    """

    def __init__(self, manager: object) -> None:
        self.manager = manager
        self._keys_by_qubit_id: dict[str, int] = {}

    def _key(self, handle: QuantumHandle) -> int:
        try:
            return self._keys_by_qubit_id[handle.qubit_id]
        except KeyError as exc:
            raise KeyError(f"unknown SeQUeNCe qubit handle {handle.qubit_id}") from exc

    def _state_for(self, handle: QuantumHandle) -> tuple[object, list[int], int]:
        key = self._key(handle)
        state = self.manager.get(key)
        keys = list(state.keys)
        try:
            target = keys.index(key)
        except ValueError as exc:
            raise RuntimeError(f"manager state for key {key} does not contain that key") from exc
        return state, keys, target

    @staticmethod
    def _expand(operator: ComplexMatrix, target: int, qubits: int) -> ComplexMatrix:
        expanded = np.array([[1]], dtype=complex)
        for index in range(qubits):
            expanded = np.kron(expanded, operator if index == target else I2)
        return expanded

    def create_epr_pair(self, pair_id: str, fidelity: float = 1.0) -> QuantumPairHandle:
        fidelity = float(np.clip(fidelity, 0.25, 1.0))
        if fidelity == 1.0:
            rho = PHI_PLUS_RHO.copy()
        else:
            rho = fidelity * PHI_PLUS_RHO + (1.0 - fidelity) / 3.0 * (
                np.eye(4, dtype=complex) - PHI_PLUS_RHO
            )
        first_key = int(self.manager.new())
        second_key = int(self.manager.new())
        self.manager.set([first_key, second_key], rho.tolist())
        first_id = f"{pair_id}:0"
        second_id = f"{pair_id}:1"
        self._keys_by_qubit_id[first_id] = first_key
        self._keys_by_qubit_id[second_id] = second_key
        return QuantumPairHandle(
            QuantumHandle(pair_id, first_id, 0),
            QuantumHandle(pair_id, second_id, 1),
        )

    def prepare_bb84(self, qubit_id: str, state_id: str, basis: int, bit: int) -> QuantumHandle:
        if basis not in (0, 1) or bit not in (0, 1):
            raise ValueError("BB84 basis and bit must be 0 or 1")
        if basis == 0:
            vector = np.array([1, 0], dtype=complex) if bit == 0 else np.array([0, 1], dtype=complex)
        else:
            vector = (
                np.array([1, 1], dtype=complex) / np.sqrt(2)
                if bit == 0
                else np.array([1, -1], dtype=complex) / np.sqrt(2)
            )
        rho = np.outer(vector, vector.conj())
        key = int(self.manager.new(rho.tolist()))
        self._keys_by_qubit_id[qubit_id] = key
        return QuantumHandle(state_id, qubit_id, 0)

    def measure_bb84(self, qubit: QuantumHandle, basis: int, rng: Generator) -> int:
        if basis not in (0, 1):
            raise ValueError("BB84 basis must be 0 or 1")
        state, keys, target = self._state_for(qubit)
        rho = np.asarray(state.state, dtype=complex)
        qubits = len(keys)
        if basis == 1:
            basis_change = self._expand(H, target, qubits)
            rho = basis_change @ rho @ basis_change.conj().T

        projectors = (
            np.diag([1, 0]).astype(complex),
            np.diag([0, 1]).astype(complex),
        )
        expanded = [self._expand(projector, target, qubits) for projector in projectors]
        probabilities = [max(0.0, float(np.real(np.trace(op @ rho)))) for op in expanded]
        total = sum(probabilities)
        if total <= 0:
            raise ValueError("measurement probabilities sum to zero")
        probabilities = [probability / total for probability in probabilities]
        outcome = int(rng.choice([0, 1], p=probabilities))
        projector = expanded[outcome]
        collapsed = projector @ rho @ projector.conj().T / probabilities[outcome]
        validate_density_matrix(collapsed)
        self.manager.set(keys, collapsed.tolist())
        return outcome

    def apply_kraus(self, qubit: QuantumHandle, operators: Sequence[ComplexMatrix]) -> None:
        state, keys, target = self._state_for(qubit)
        transformed = apply_to_subsystem(
            np.asarray(state.state, dtype=complex),
            list(operators),
            target,
            len(keys),
        )
        self.manager.set(keys, transformed.tolist())

    def fidelity_to_bell_phi_plus(self, pair: QuantumPairHandle) -> float:
        first_key = self._key(pair.first)
        second_key = self._key(pair.second)
        state = self.manager.get(first_key)
        keys = list(state.keys)
        rho = np.asarray(state.state, dtype=complex)
        expected = [first_key, second_key]
        if keys == expected:
            ordered = rho
        elif keys == list(reversed(expected)):
            swap = np.array(
                [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
                dtype=complex,
            )
            ordered = swap @ rho @ swap.conj().T
        else:
            raise ValueError("Bell fidelity is only defined for the two-qubit QPV pair")
        return float(np.real(PHI_PLUS.conj().T @ ordered @ PHI_PLUS))
