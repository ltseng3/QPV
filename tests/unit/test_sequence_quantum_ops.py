"""Contract tests for the SeQUeNCe quantum-manager adapter.

A tiny manager double exercises the documented SeQUeNCe 1.0.0 ``new/get/set``
contract without requiring the external package in the portable CI lane.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from qorchsim.adapters.sequence.quantum_ops import SequenceQuantumOperations
from qorchsim.quantum.kraus import phase_damping_from_coherence


@dataclass
class _State:
    state: np.ndarray
    keys: list[int]


class _ManagerDouble:
    def __init__(self) -> None:
        self.states: dict[int, _State] = {}
        self.next_key = 0

    def new(self, state=((1 + 0j, 0j), (0j, 0j))) -> int:
        key = self.next_key
        self.next_key += 1
        self.states[key] = _State(np.asarray(state, dtype=complex), [key])
        return key

    def get(self, key: int) -> _State:
        return self.states[key]

    def set(self, keys: list[int], state) -> None:
        shared = _State(np.asarray(state, dtype=complex), list(keys))
        for key in keys:
            self.states[key] = shared


def test_sequence_quantum_manager_adapter_epr_and_measurement() -> None:
    operations = SequenceQuantumOperations(_ManagerDouble())
    pair = operations.create_epr_pair("pair")
    assert operations.fidelity_to_bell_phi_plus(pair) == pytest.approx(1.0)

    rng = np.random.default_rng(12)
    first = operations.measure_bb84(pair.first, 1, rng)
    second = operations.measure_bb84(pair.second, 1, rng)
    assert first == second


def test_sequence_quantum_manager_adapter_kraus_and_bb84_prepare() -> None:
    manager = _ManagerDouble()
    operations = SequenceQuantumOperations(manager)
    qubit = operations.prepare_bb84("q", "state", basis=1, bit=0)
    operations.apply_kraus(qubit, phase_damping_from_coherence(0.5))
    state = manager.get(0).state
    assert np.isclose(np.trace(state), 1.0)
    assert np.isclose(state[0, 1], 0.25)
