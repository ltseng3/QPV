import pytest

from qorchsim.cloudsim.resources import DeviceResource, ResourceSnapshot
from qorchsim.errors import InvalidStateTransitionError
from qorchsim.network.geometry import Position
from qorchsim.policies.freshness import validate_freshness
from qorchsim.policies.schedule import ScheduleBounds, SchedulePolicy
from qorchsim.policies.telemetry import BaselineTelemetryPolicy, SecurityTelemetryPolicy, TelemetryBounds
from qorchsim.qpv.controller import ControllerStateMachine
from qorchsim.qpv.models import ControllerRoundState, ProverRoundState, VerifierRoundState
from qorchsim.qpv.plans import RoundPlan
from qorchsim.qpv.prover import ProverStateMachine
from qorchsim.qpv.verifier import VerifierStateMachine


def test_prover_state_machine_accepts_only_declared_transitions() -> None:
    machine = ProverStateMachine()
    machine.transition(ProverRoundState.QND_IN_PROGRESS)
    machine.transition(ProverRoundState.MEMORY_LOADING)
    machine.transition(ProverRoundState.COMMITTED_WITH_STATE)
    machine.transition(ProverRoundState.WAITING_FOR_BASIS)
    with pytest.raises(InvalidStateTransitionError):
        machine.transition(ProverRoundState.ANSWER_SENT)


def test_verifier_and_controller_state_machines() -> None:
    verifier = VerifierStateMachine()
    verifier.transition(VerifierRoundState.PREPARING)
    verifier.transition(VerifierRoundState.CHALLENGE_SENT)
    verifier.transition(VerifierRoundState.BASIS_SENT)
    controller = ControllerStateMachine()
    controller.transition(ControllerRoundState.PLANNING)
    controller.transition(ControllerRoundState.PLAN_DISTRIBUTED)
    controller.transition(ControllerRoundState.COLLECTING_REPORTS)


def test_freshness_policy_reason_codes() -> None:
    decision = validate_freshness(
        expected_nonce="new", actual_nonce="old", expected_epoch=2, actual_epoch=1, authentic=False
    )
    assert not decision.accepted
    assert set(decision.reason_codes) == {"unauthenticated", "nonce_mismatch", "telemetry_epoch_mismatch"}


def test_schedule_policy_bounds() -> None:
    plan = RoundPlan(
        "s", "r", 0, "n", 1, 100, 50, 300, {"v0": 1}, {"v0": 2}, Position(0), 10
    )
    decision = SchedulePolicy(ScheduleBounds(0, 150, 50)).validate(plan)
    assert not decision.accepted
    assert "x_delta_out_of_bounds" in decision.reason_codes
    assert "y_delta_out_of_bounds" in decision.reason_codes
    assert "basis_skew_out_of_bounds" in decision.reason_codes


def test_telemetry_policy_accepts_baseline_and_rejects_poisoned() -> None:
    snapshot = ResourceSnapshot(
        0,
        (),
        (
            DeviceResource(
                "memory", "p", "quantum_memory", {"t2_ps": 10}, {"t2_ps": 100}
            ),
        ),
        (),
        1,
    )
    assert BaselineTelemetryPolicy().validate(snapshot, 0).accepted
    decision = SecurityTelemetryPolicy(TelemetryBounds(maximum_t2_ps=50)).validate(snapshot, 0)
    assert not decision.accepted
    assert any("reported_t2" in reason for reason in decision.reason_codes)
