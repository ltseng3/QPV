"""SeQUeNCE-backed smoke test.

This test is skipped when SeQUeNCE 1.0.0 is not installed. The portable CI lane
still tests the adapter's quantum-manager contract with a manager double.
"""

from __future__ import annotations

import importlib.metadata

import pytest

sequence = pytest.importorskip("sequence")

from qorchsim.adapters.sequence.scenario_builder import build_sequence_backend
from qorchsim.adapters.sequence.version import SUPPORTED_SEQUENCE_VERSION


@pytest.mark.sequence
def test_sequence_backend_dispatches_events() -> None:
    assert importlib.metadata.version("sequence") == SUPPORTED_SEQUENCE_VERSION
    bus, scheduler, quantum = build_sequence_backend(stop_time_ps=1_000)
    received = []
    bus.subscribe("smoke", received.append)

    from qorchsim.core.events import DomainEvent, EventPhase
    from qorchsim.types import SimTimePs

    scheduler.schedule_at(
        SimTimePs(10),
        EventPhase.PROTOCOL,
        DomainEvent(event_id="sequence-smoke", event_type="smoke", payload={}),
    )
    scheduler.run()
    assert [event.event_id for event in received] == ["sequence-smoke"]
    pair = quantum.create_epr_pair("smoke-pair")
    assert quantum.fidelity_to_bell_phi_plus(pair) == pytest.approx(1.0)
