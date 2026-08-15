"""Bindings for framework-backed physical device components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SequenceDeviceBinding:
    """Map a portable resource identifier to a SeQUeNCe component object."""

    resource_id: str
    node_id: str
    kind: str
    sequence_component: Any

    def attribute(self, name: str) -> Any:
        """Read a required component attribute with a useful adapter error."""
        if not hasattr(self.sequence_component, name):
            raise AttributeError(
                f"SeQUeNCe component {self.resource_id!r} has no attribute {name!r}"
            )
        return getattr(self.sequence_component, name)
