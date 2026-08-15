from qorchsim.attacks.base import AttackContext
from qorchsim.attacks.schedule_skew import ScheduleSkewAttack
from qorchsim.attacks.selective_jamming import SelectiveJammingAttack
from qorchsim.attacks.timestamp_forgery import TimestampForgeryAttack
from qorchsim.core.random_streams import RandomStreams
from qorchsim.network.geometry import Position
from qorchsim.network.transmissions import ClassicalTransmission
from qorchsim.qpv.models import VerifierReport
from qorchsim.qpv.plans import RoundPlan


def context() -> AttackContext:
    return AttackContext(0, "s", "r", RandomStreams(1).generator("a"))


def test_schedule_skew_returns_replacement_plan() -> None:
    plan = RoundPlan("s", "r", 0, "n", 1, 100, 200, 200, {"v0": 1}, {"v0": 2}, Position(0), 10)
    attacked = ScheduleSkewAttack("a", x_shift_ps=-10).alter_plan(plan, context())
    assert attacked is not plan
    assert attacked.x_send_ps == 190
    assert plan.x_send_ps == 200


def test_jamming_drops_targeted_message() -> None:
    tx = ClassicalTransmission("t", "l", "a", "b", "answer", {}, 0, 10)
    attack = SelectiveJammingAttack("jam", link_ids=("l",), drop_probability=1.0)
    assert attack.alter_classical(tx, context())[0].dropped


def test_timestamp_forgery_preserves_physical_time() -> None:
    report = VerifierReport("s", "r", "v0", "n", 1, 1, 0, 0, 10, 11, 11, 20, 21, 21, 30, 40)
    attacked = TimestampForgeryAttack("forge", "v0", -5, ("answer_arrival",)).alter_report(report, context())
    assert attacked.answer_physical_ps == 20
    assert attacked.answer_local_ps == 21
    assert attacked.answer_reported_ps == 16
