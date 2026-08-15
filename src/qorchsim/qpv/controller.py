"""Controller state machine."""

from __future__ import annotations

from qorchsim.core.lifecycle import validate_transition
from qorchsim.qpv.models import ControllerRoundState

_ALLOWED = {
    ControllerRoundState.CALIBRATING: {ControllerRoundState.PLANNING, ControllerRoundState.ABORTED},
    ControllerRoundState.PLANNING: {ControllerRoundState.PLAN_DISTRIBUTED, ControllerRoundState.REJECTED},
    ControllerRoundState.PLAN_DISTRIBUTED: {ControllerRoundState.COLLECTING_REPORTS},
    ControllerRoundState.COLLECTING_REPORTS: {ControllerRoundState.DECIDING, ControllerRoundState.ABORTED},
    ControllerRoundState.DECIDING: {ControllerRoundState.ACCEPTED, ControllerRoundState.REJECTED},
    ControllerRoundState.ACCEPTED: set(),
    ControllerRoundState.REJECTED: set(),
    ControllerRoundState.ABORTED: set(),
}


class ControllerStateMachine:
    """Explicit controller state transitions."""

    def __init__(self) -> None:
        self.state = ControllerRoundState.CALIBRATING

    def transition(self, target: ControllerRoundState) -> None:
        validate_transition(self.state, target, _ALLOWED)
        self.state = target
