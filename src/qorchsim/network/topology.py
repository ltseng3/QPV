"""Portable topology model."""

from __future__ import annotations

from dataclasses import dataclass

from qorchsim.network.geometry import Position, distance


@dataclass(frozen=True, slots=True)
class NodeSpec:
    node_id: str
    position: Position


@dataclass(frozen=True, slots=True)
class LinkSpec:
    link_id: str
    source: str
    destination: str
    kind: str
    explicit_length_m: float | None = None


@dataclass(frozen=True, slots=True)
class Topology:
    nodes: dict[str, NodeSpec]
    links: tuple[LinkSpec, ...]

    def link_length(self, link: LinkSpec) -> float:
        if link.explicit_length_m is not None:
            return link.explicit_length_m
        return distance(self.nodes[link.source].position, self.nodes[link.destination].position)
