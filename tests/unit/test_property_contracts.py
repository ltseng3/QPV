"""Optional property-based tests; installed by the ``dev`` extra."""

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st

from qorchsim.attacks.base import AttackContext, IdentityAttack
from qorchsim.core.random_streams import RandomStreams
from qorchsim.network.transmissions import ClassicalTransmission


@given(st.integers(min_value=0, max_value=10**12))
def test_identity_attack_preserves_transmission(delay: int) -> None:
    tx = ClassicalTransmission("t", "l", "a", "b", "answer", {}, 0, delay)
    ctx = AttackContext(0, "s", "r", RandomStreams(1).generator("a"))
    assert IdentityAttack().alter_classical(tx, ctx) == (tx,)
