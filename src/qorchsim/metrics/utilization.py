"""Simple utilization metrics extension seam."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UtilizationCounters:
    source_operations: int = 0
    qnd_operations: int = 0
    memory_loads: int = 0
    memory_retrievals: int = 0
    measurements: int = 0
    classical_transmissions: int = 0
    quantum_transmissions: int = 0
    drops: int = 0
