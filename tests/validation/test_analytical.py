import math

from qorchsim.network.geometry import Position, delay_to_distance_m, propagation_delay_ps
from qorchsim.quantum.noise import memory_channels


def test_one_kilometre_fibre_delay() -> None:
    assert propagation_delay_ps(Position(0), Position(1000), 2e8) == 5_000_000


def test_one_microsecond_round_trip_tolerance() -> None:
    assert delay_to_distance_m(1_000_000, 2e8) == 100


def test_memory_channel_parameters_follow_exponential() -> None:
    channels = memory_channels(1_000, 1_000, None)
    k0 = channels[0][0]
    excited_amplitude = float(abs(k0[1, 1]) ** 2)
    assert math.isclose(excited_amplitude, math.exp(-1), rel_tol=1e-9)
