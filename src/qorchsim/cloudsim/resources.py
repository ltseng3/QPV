"""Portable resource inventory visible to schedulers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class NodeResource:
    node_id: str
    position_m: tuple[float, float]
    trust: float = 1.0


@dataclass(frozen=True, slots=True)
class DeviceResource:
    resource_id: str
    node_id: str
    kind: str
    physical_capabilities: Mapping[str, object]
    reported_capabilities: Mapping[str, object]
    state: str = "idle"
    attack_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LinkResource:
    resource_id: str
    source: str
    destination: str
    kind: str
    length_m: float
    available: bool = True


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    observed_at_ps: int
    nodes: tuple[NodeResource, ...]
    devices: tuple[DeviceResource, ...]
    links: tuple[LinkResource, ...]
    telemetry_epoch: int
