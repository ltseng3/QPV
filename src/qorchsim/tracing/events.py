"""Canonical trace event schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TraceEvent:
    schema_version: str
    run_id: str
    session_id: str | None
    round_id: str | None
    event_id: str
    physical_time_ps: int
    phase: str
    node_id: str | None
    component_id: str | None
    event_type: str
    local_time_ps: int | None = None
    reported_time_ps: int | None = None
    transmission_id: str | None = None
    quantum_object_id: str | None = None
    attack_ids: tuple[str, ...] = ()
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["attack_ids"] = list(self.attack_ids)
        return value
