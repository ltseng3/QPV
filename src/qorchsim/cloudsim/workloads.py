"""CloudSim-compatible workload abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Workload:
    workload_id: str
    workload_type: str
    arrival_time_ps: int
    deadline_ps: int | None
    priority: int
    parameters: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class QpvWorkload(Workload):
    session_spec: object
