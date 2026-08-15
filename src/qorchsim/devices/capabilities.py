"""Immutable device capability profiles."""

from __future__ import annotations

from dataclasses import dataclass

from qorchsim.types import DurationPs


@dataclass(frozen=True, slots=True)
class EprSourceCapabilities:
    generation_latency_ps: DurationPs
    generation_success_probability: float
    pair_fidelity: float
    repetition_rate_hz: float


@dataclass(frozen=True, slots=True)
class QndCapabilities:
    operation_latency_ps: DurationPs
    detection_efficiency: float
    dark_count_rate_hz: float
    state_survival_probability: float
    disturbance_probability: float
    dead_time_ps: DurationPs
    gate_width_ps: DurationPs


@dataclass(frozen=True, slots=True)
class MemoryCapabilities:
    load_latency_ps: DurationPs
    retrieve_latency_ps: DurationPs
    load_efficiency: float
    retrieve_efficiency: float
    t1_ps: DurationPs | None
    t2_ps: DurationPs | None
    maximum_hold_ps: DurationPs | None


@dataclass(frozen=True, slots=True)
class MeasurementCapabilities:
    basis_switch_latency_ps: DurationPs
    measurement_latency_ps: DurationPs
    measurement_fidelity: float
    dead_time_ps: DurationPs


@dataclass(frozen=True, slots=True)
class ClockCapabilities:
    epoch_physical_ps: int
    offset_ps: int
    drift_ppm: float
    jitter_stddev_ps: float
    resolution_ps: int
