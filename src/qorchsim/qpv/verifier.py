"""Verifier state machine."""

from __future__ import annotations

from qorchsim.core.lifecycle import validate_transition
from qorchsim.qpv.models import VerifierRoundState

_ALLOWED = {
    VerifierRoundState.PLANNED: {VerifierRoundState.PREPARING, VerifierRoundState.ABORTED},
    VerifierRoundState.PREPARING: {
        VerifierRoundState.CHALLENGE_SENT,
        VerifierRoundState.BASIS_SENT,
        VerifierRoundState.ABORTED,
    },
    VerifierRoundState.CHALLENGE_SENT: {VerifierRoundState.BASIS_SENT, VerifierRoundState.ABORTED},
    VerifierRoundState.BASIS_SENT: {
        VerifierRoundState.COMMITMENT_RECEIVED,
        VerifierRoundState.LOCAL_MEASUREMENT_COMPLETE,
        VerifierRoundState.ABORTED,
    },
    VerifierRoundState.COMMITMENT_RECEIVED: {
        VerifierRoundState.LOCAL_MEASUREMENT_COMPLETE,
        VerifierRoundState.ANSWER_RECEIVED,
        VerifierRoundState.ABORTED,
    },
    VerifierRoundState.LOCAL_MEASUREMENT_COMPLETE: {
        VerifierRoundState.ANSWER_RECEIVED,
        VerifierRoundState.REPORT_SENT,
        VerifierRoundState.ABORTED,
    },
    VerifierRoundState.ANSWER_RECEIVED: {VerifierRoundState.REPORT_SENT, VerifierRoundState.ABORTED},
    VerifierRoundState.REPORT_SENT: {VerifierRoundState.COMPLETE},
    VerifierRoundState.ABORTED: {VerifierRoundState.COMPLETE},
    VerifierRoundState.COMPLETE: set(),
}


class VerifierStateMachine:
    """Explicit verifier state transitions."""

    def __init__(self) -> None:
        self.state = VerifierRoundState.PLANNED

    def transition(self, target: VerifierRoundState) -> None:
        validate_transition(self.state, target, _ALLOWED)
        self.state = target
