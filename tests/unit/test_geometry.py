from qorchsim.network.geometry import Position, causal_margin_m, delay_to_distance_m, distance, propagation_delay_ps


def test_geometry_and_propagation() -> None:
    a = Position(0, 0)
    b = Position(3, 4)
    assert distance(a, b) == 5
    assert propagation_delay_ps(Position(0), Position(1000), 2e8) == 5_000_000
    assert delay_to_distance_m(1_000_000, 2e8) == 100


def test_causal_margin_sign() -> None:
    assert causal_margin_m(Position(0), 0, Position(1000), 1_000_000) > 0
    assert causal_margin_m(Position(0), 0, Position(1000), 10_000_000) < 0
