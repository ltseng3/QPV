"""Reusable state transition validation."""

from __future__ import annotations

from collections.abc import Mapping, Set
from enum import Enum
from typing import TypeVar

from qorchsim.errors import InvalidStateTransitionError

StateT = TypeVar("StateT", bound=Enum)


def validate_transition(current: StateT, target: StateT, allowed: Mapping[StateT, Set[StateT]]) -> None:
    """Raise if a state transition is not explicitly allowed."""
    if target not in allowed.get(current, set()):
        raise InvalidStateTransitionError(f"invalid transition: {current.value} -> {target.value}")
