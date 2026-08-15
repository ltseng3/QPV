from __future__ import annotations

import pytest

from qorchsim.adapters.sequence.channels import SequenceChannelBinding
from qorchsim.adapters.sequence.devices import SequenceDeviceBinding
from qorchsim.adapters.sequence.nodes import SequenceNodeBinding
from qorchsim.adapters.sequence.protocols import DomainProtocolBridge


def test_sequence_node_binding_validates_required_method() -> None:
    class NodeDouble:
        def send_message(self) -> None:
            return None

    binding = SequenceNodeBinding("v0", NodeDouble())
    binding.require_method("send_message")
    with pytest.raises(TypeError, match="receive_qubit"):
        binding.require_method("receive_qubit")


def test_sequence_channel_binding_enforces_direction() -> None:
    binding = SequenceChannelBinding("q-v0-p", "v0", "prover", "quantum", object())
    binding.validate_direction("v0", "prover")
    with pytest.raises(ValueError, match="not 'prover' -> 'v0'"):
        binding.validate_direction("prover", "v0")


def test_sequence_device_binding_reads_required_attributes() -> None:
    class ComponentDouble:
        efficiency = 0.9

    binding = SequenceDeviceBinding("prover.qnd", "prover", "qnd", ComponentDouble())
    assert binding.attribute("efficiency") == 0.9
    with pytest.raises(AttributeError, match="dark_count_rate"):
        binding.attribute("dark_count_rate")


def test_domain_protocol_bridge_delivers_decoded_message() -> None:
    received: list[tuple[str, dict[str, int]]] = []
    bridge = DomainProtocolBridge("prover", lambda source, message: received.append((source, message)))
    bridge.deliver("v0", {"round": 7})
    assert received == [("v0", {"round": 7})]
