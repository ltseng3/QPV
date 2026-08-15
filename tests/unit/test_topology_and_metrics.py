from qorchsim.metrics.aggregation import continuous_summary, wilson_interval
from qorchsim.network.geometry import Position
from qorchsim.network.link_state import LinkState
from qorchsim.network.topology import LinkSpec, NodeSpec, Topology
from qorchsim.qpv.timing import commitment_margin_ps, memory_margin_ps, response_margin_ps


def test_topology_uses_explicit_or_geometric_length() -> None:
    topology = Topology(
        {"a": NodeSpec("a", Position(0)), "b": NodeSpec("b", Position(3, 4))},
        (),
    )
    assert topology.link_length(LinkSpec("l1", "a", "b", "q")) == 5
    assert topology.link_length(LinkSpec("l2", "a", "b", "q", 9)) == 9
    assert LinkState("l").available


def test_metric_helpers_cover_empty_and_nonempty_inputs() -> None:
    assert wilson_interval(0, 0) == (0.0, 0.0)
    low, high = wilson_interval(5, 10)
    assert 0 <= low < 0.5 < high <= 1
    assert continuous_summary([])["count"] == 0
    summary = continuous_summary([1, 2, 3])
    assert summary["mean"] == 2
    assert summary["median"] == 2


def test_timing_helpers() -> None:
    assert commitment_margin_ps(10, 4) == 6
    assert commitment_margin_ps(None, 4) is None
    assert response_margin_ps(20, 15) == 5
    assert response_margin_ps(20, None) is None
    assert memory_margin_ps(100, 60) == 40
    assert memory_margin_ps(None, 60) is None
