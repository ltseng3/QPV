"""Logical-to-SeQUeNCE channel binding values.

Version 1 computes QPV geometry and adversarial delay/drop transformations in portable
QOrchSim models, then schedules resulting arrivals on the SeQUeNCe timeline.  This
module defines the stable adapter record used when direct SeQUeNCe optical/classical
channel components are introduced later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ChannelKind = Literal["quantum", "classical"]


@dataclass(frozen=True, slots=True)
class SequenceChannelBinding:
    """Bind a portable directional link identifier to a framework channel object."""

    link_id: str
    source_node_id: str
    destination_node_id: str
    kind: ChannelKind
    sequence_channel: Any

    def validate_direction(self, source: str, destination: str) -> None:
        """Reject accidental use of a directional link in the reverse direction."""
        if (source, destination) != (self.source_node_id, self.destination_node_id):
            raise ValueError(
                f"link {self.link_id!r} is {self.source_node_id!r} -> "
                f"{self.destination_node_id!r}, not {source!r} -> {destination!r}"
            )
