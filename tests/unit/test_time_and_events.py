from qorchsim.core.clock import causal_seconds_to_ps, seconds_to_ps
from qorchsim.core.events import EventPhase, SEQUENCE_STRIDE, encode_priority


def test_time_rounding() -> None:
    assert seconds_to_ps(1e-9) == 1_000
    assert causal_seconds_to_ps(1.0001e-12) == 2


def test_priority_encoding_orders_phases() -> None:
    assert encode_priority(EventPhase.PHYSICAL_ARRIVAL, 9) < encode_priority(EventPhase.TIMEOUT, 0)
    assert encode_priority(EventPhase.PROTOCOL, 2) == int(EventPhase.PROTOCOL) * SEQUENCE_STRIDE + 2
