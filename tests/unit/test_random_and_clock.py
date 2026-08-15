from qorchsim.core.random_streams import RandomStreams
from qorchsim.devices.capabilities import ClockCapabilities
from qorchsim.devices.local_clock import LocalClock


def test_named_streams_are_reproducible() -> None:
    a = RandomStreams(7).generator("round/0").integers(0, 100, size=5).tolist()
    b = RandomStreams(7).generator("round/0").integers(0, 100, size=5).tolist()
    assert a == b


def test_local_clock_offset_drift_and_resolution() -> None:
    rng = RandomStreams(1).generator("clock")
    clock = LocalClock(ClockCapabilities(0, 100, 10.0, 0.0, 10), rng)
    assert clock.observe(1_000_000) == 1_000_110
