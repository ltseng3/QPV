"""Workload allocation values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Allocation:
    allocation_id: str
    workload_id: str
    node_bindings: Mapping[str, str]
    device_bindings: Mapping[str, str]
    link_bindings: Mapping[str, str]
    start_time_ps: int
    end_time_ps: int
