"""Prover state machine."""

from __future__ import annotations

from qorchsim.core.lifecycle import validate_transition
from qorchsim.qpv.models import ProverRoundState

_ALLOWED = {
    ProverRoundState.WAITING_FOR_CHALLENGE: {
        ProverRoundState.QND_IN_PROGRESS,
        ProverRoundState.NO_COMMITMENT,
        ProverRoundState.ABORTED,
    },
    ProverRoundState.QND_IN_PROGRESS: {
        ProverRoundState.MEMORY_LOADING,
        ProverRoundState.COMMITTED_WITHOUT_STATE,
        ProverRoundState.NO_COMMITMENT,
        ProverRoundState.ABORTED,
    },
    ProverRoundState.MEMORY_LOADING: {
        ProverRoundState.COMMITTED_WITH_STATE,
        ProverRoundState.NO_COMMITMENT,
        ProverRoundState.ABORTED,
    },
    ProverRoundState.COMMITTED_WITH_STATE: {
        ProverRoundState.WAITING_FOR_BASIS,
        ProverRoundState.MEMORY_RETRIEVING,
        ProverRoundState.ABORTED,
    },
    ProverRoundState.COMMITTED_WITHOUT_STATE: {
        ProverRoundState.WAITING_FOR_BASIS,
        ProverRoundState.COMPLETE,
        ProverRoundState.ABORTED,
    },
    ProverRoundState.WAITING_FOR_BASIS: {
        ProverRoundState.MEMORY_RETRIEVING,
        ProverRoundState.COMPLETE,
        ProverRoundState.ABORTED,
    },
    ProverRoundState.MEMORY_RETRIEVING: {ProverRoundState.MEASURING, ProverRoundState.ABORTED},
    ProverRoundState.MEASURING: {ProverRoundState.ANSWER_SENT, ProverRoundState.ABORTED},
    ProverRoundState.ANSWER_SENT: {ProverRoundState.COMPLETE},
    ProverRoundState.NO_COMMITMENT: {ProverRoundState.COMPLETE},
    ProverRoundState.ABORTED: {ProverRoundState.COMPLETE},
    ProverRoundState.COMPLETE: set(),
}


class ProverStateMachine:
    """Explicit prover state transitions."""

    def __init__(self) -> None:
        self.state = ProverRoundState.WAITING_FOR_CHALLENGE

    def transition(self, target: ProverRoundState) -> None:
        validate_transition(self.state, target, _ALLOWED)
        self.state = target
