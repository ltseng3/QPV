"""Quantum handles and density-state store."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

ComplexMatrix = NDArray[np.complex128]


@dataclass(frozen=True, slots=True)
class QuantumHandle:
    """Reference to one qubit within a shared density matrix."""

    state_id: str
    qubit_id: str
    index: int


@dataclass(frozen=True, slots=True)
class QuantumPairHandle:
    """Two handles that initially share an EPR density matrix."""

    first: QuantumHandle
    second: QuantumHandle


@dataclass
class QuantumState:
    """Mutable density state internal to a QuantumStateStore."""

    qubit_ids: list[str]
    rho: ComplexMatrix


class QuantumStateStore:
    """Own composite density matrices and qubit references."""

    def __init__(self) -> None:
        self._states: dict[str, QuantumState] = {}

    def put(self, state_id: str, qubit_ids: list[str], rho: ComplexMatrix) -> list[QuantumHandle]:
        if state_id in self._states:
            raise ValueError(f"duplicate quantum state {state_id}")
        self._states[state_id] = QuantumState(qubit_ids=list(qubit_ids), rho=np.asarray(rho, dtype=complex))
        return [QuantumHandle(state_id, qubit_id, index) for index, qubit_id in enumerate(qubit_ids)]

    def state(self, handle: QuantumHandle) -> QuantumState:
        return self._states[handle.state_id]

    def replace(self, handle: QuantumHandle, rho: ComplexMatrix) -> None:
        self.state(handle).rho = np.asarray(rho, dtype=complex)

    def qubit_count(self, handle: QuantumHandle) -> int:
        return len(self.state(handle).qubit_ids)

    def create_single(self, state_id: str, qubit_id: str, rho: ComplexMatrix) -> QuantumHandle:
        return self.put(state_id, [qubit_id], rho)[0]

    def clone_single_from_bit(self, state_id: str, qubit_id: str, basis: int, bit: int) -> QuantumHandle:
        if basis == 0:
            vector = np.array([1, 0], dtype=complex) if bit == 0 else np.array([0, 1], dtype=complex)
        else:
            vector = (
                np.array([1, 1], dtype=complex) / np.sqrt(2)
                if bit == 0
                else np.array([1, -1], dtype=complex) / np.sqrt(2)
            )
        return self.create_single(state_id, qubit_id, np.outer(vector, vector.conj()))
