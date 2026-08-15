"""Logical-to-SeQUeNCe node binding values.

The version-1 QPV runtime owns protocol state machines in the domain layer instead of
subclassing SeQUeNCe ``Node`` directly.  These immutable bindings record the adapter
metadata needed when a future backend maps a logical QOrchSim node to a concrete
SeQUeNCe node object.  Keeping this mapping in the adapter package prevents framework
objects from leaking into scheduler, workload, attack, or metric APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SequenceNodeBinding:
    """Associate one logical node identifier with a SeQUeNCe node instance.

    ``sequence_node`` is deliberately typed as ``Any``.  Importing SeQUeNCe's concrete
    ``Node`` type here would make documentation and portable tests require the optional
    runtime package.  The integration builder is responsible for validating the object.
    """

    logical_node_id: str
    sequence_node: Any

    def require_method(self, method_name: str) -> None:
        """Raise a descriptive error when the bound node lacks an expected method."""
        if not callable(getattr(self.sequence_node, method_name, None)):
            raise TypeError(
                f"SeQUeNCe node for {self.logical_node_id!r} does not expose "
                f"callable {method_name!r}"
            )
