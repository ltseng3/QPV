"""Link resources and utilization counters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkState:
    link_id: str
    available: bool = True
    transmissions: int = 0
    drops: int = 0
