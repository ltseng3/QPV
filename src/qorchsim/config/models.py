"""Pydantic configuration schema."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qorchsim.errors import ConfigurationError

_UNIT_PS = {
    "ps": 1,
    "ns": 1_000,
    "us": 1_000_000,
    "µs": 1_000_000,
    "ms": 1_000_000_000,
    "s": 1_000_000_000_000,
}
_DURATION_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(ps|ns|us|µs|ms|s)\s*$", re.I)


def parse_duration_ps(value: str | int | float | None) -> int | None:
    """Parse a human duration or raw picoseconds."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a duration")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("duration must be nonnegative")
        return value
    if isinstance(value, float):
        if value < 0:
            raise ValueError("duration must be nonnegative")
        return int(round(value))
    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError(f"invalid duration {value!r}; use ps/ns/us/ms/s")
    amount, unit = match.groups()
    return int(round(float(amount) * _UNIT_PS[unit.lower()]))


Duration = Annotated[int | str | float, Field(description="Duration with unit or raw picoseconds")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class SimulationConfig(StrictModel):
    seed: int = 12345
    stop_time: Duration = "100 ms"
    rounds: int = Field(default=100, ge=1)
    quantum_formalism: Literal["density_matrix"] = "density_matrix"
    cleanup_margin: Duration = "10 us"

    @field_validator("stop_time", "cleanup_margin", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class ExecutionConfig(StrictModel):
    model: Literal["sequence_qpv", "portable_qpv"] = "sequence_qpv"
    parallel_processes: int = Field(default=1, ge=1)
    allow_unsupported_sequence_version: bool = False


class PositionConfig(StrictModel):
    x_m: float
    y_m: float = 0.0


class GeometryConfig(StrictModel):
    dimension: Literal[1, 2] = 1
    propagation_speed_quantum_m_s: float = Field(default=2.0e8, gt=0)
    propagation_speed_classical_m_s: float = Field(default=2.0e8, gt=0)
    nodes: dict[str, PositionConfig]


class EprSourceConfig(StrictModel):
    generation_latency: Duration = "100 ns"
    success_probability: float = Field(default=1.0, ge=0, le=1)
    pair_fidelity: float = Field(default=1.0, ge=0.25, le=1)
    repetition_rate_hz: float = Field(default=1e6, gt=0)

    @field_validator("generation_latency", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class MemoryConfig(StrictModel):
    load_latency: Duration = "200 ns"
    retrieve_latency: Duration = "200 ns"
    load_efficiency: float = Field(default=1.0, ge=0, le=1)
    retrieve_efficiency: float = Field(default=1.0, ge=0, le=1)
    t1: Duration | None = None
    t2: Duration | None = None
    maximum_hold: Duration | None = None

    @field_validator("load_latency", "retrieve_latency", "t1", "t2", "maximum_hold", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)

    @model_validator(mode="after")
    def _physical(self):
        if self.t1 is not None and self.t2 is not None and int(self.t2) > 2 * int(self.t1):
            raise ValueError("physical model requires T2 <= 2*T1")
        return self


class MeasurementConfig(StrictModel):
    basis_switch_latency: Duration = "50 ns"
    measurement_latency: Duration = "200 ns"
    measurement_fidelity: float = Field(default=1.0, ge=0, le=1)
    dead_time: Duration = "100 ns"

    @field_validator("basis_switch_latency", "measurement_latency", "dead_time", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class QndConfig(StrictModel):
    operation_latency: Duration = "300 ns"
    efficiency: float = Field(default=1.0, ge=0, le=1)
    dark_count_rate_hz: float = Field(default=0, ge=0)
    state_survival_probability: float = Field(default=1.0, ge=0, le=1)
    disturbance_probability: float = Field(default=0, ge=0, le=1)
    dead_time: Duration = "100 ns"
    gate_width: Duration = "2 us"

    @field_validator("operation_latency", "dead_time", "gate_width", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class VerifierHardwareConfig(StrictModel):
    epr_source: EprSourceConfig | None = None
    memory: MemoryConfig
    measurement: MeasurementConfig


class ProverHardwareConfig(StrictModel):
    qnd: QndConfig
    memory: MemoryConfig
    measurement: MeasurementConfig


class HardwareConfig(StrictModel):
    v0: VerifierHardwareConfig
    prover: ProverHardwareConfig


class QuantumLinkConfig(StrictModel):
    id: str
    source: str
    destination: str
    attenuation_db_per_m: float = Field(default=0.0, ge=0)
    polarization_fidelity: float = Field(default=1.0, ge=0, le=1)
    frequency_hz: float = Field(default=8e7, gt=0)
    length_m: float | None = Field(default=None, gt=0)


class ClassicalLinkConfig(StrictModel):
    id: str
    source: str
    destination: str
    sender_delay: Duration = 0
    length_m: float | None = Field(default=None, gt=0)

    @field_validator("sender_delay", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class LinksConfig(StrictModel):
    quantum: tuple[QuantumLinkConfig, ...]
    classical: tuple[ClassicalLinkConfig, ...]


class ProtocolConfig(StrictModel):
    basis_function: Literal["xor"] = "xor"
    challenge_to_basis_delay: Duration = "5 us"
    commitment_window: Duration = "2 us"
    response_slack: Duration = "1 us"
    minimum_committed_rounds: int = Field(default=1, ge=0)
    maximum_qber: float = Field(default=0.1, ge=0, le=1)
    maximum_timing_violations: int = Field(default=0, ge=0)
    maximum_authenticated_radius_m: float = Field(default=100, gt=0)
    initial_start: Duration = "1 us"

    @field_validator(
        "challenge_to_basis_delay",
        "commitment_window",
        "response_slack",
        "initial_start",
        mode="before",
    )
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class ControllerConfig(StrictModel):
    policy: Literal["baseline", "security_aware"] = "baseline"
    calibration_age_limit: Duration = "60 s"
    clock_uncertainty: Duration = "50 ns"
    maximum_reported_t2: Duration | None = None
    maximum_basis_skew: Duration = "100 ns"

    @field_validator(
        "calibration_age_limit",
        "clock_uncertainty",
        "maximum_reported_t2",
        "maximum_basis_skew",
        mode="before",
    )
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class ScheduleSkewAttackConfig(StrictModel):
    type: Literal["schedule_skew"]
    id: str = "schedule-skew"
    mode: Literal["early_basis", "late_basis", "asymmetric"] = "asymmetric"
    x_shift: Duration = 0
    y_shift: Duration = 0
    challenge_shift: Duration = 0
    modify_controller_view: bool = False

    @field_validator("x_shift", "y_shift", "challenge_shift", mode="before")
    @classmethod
    def _duration(cls, value):
        # Shifts may be signed strings.
        if isinstance(value, str) and value.strip().startswith("-"):
            return -int(parse_duration_ps(value.strip()[1:]) or 0)
        return parse_duration_ps(value)


class TelemetryPoisoningAttackConfig(StrictModel):
    type: Literal["telemetry_poisoning"]
    id: str = "telemetry-poisoning"
    resource_id: str
    fields: dict[str, object]


class TimestampForgeryAttackConfig(StrictModel):
    type: Literal["timestamp_forgery"]
    id: str = "timestamp-forgery"
    node_id: str
    bias: Duration
    fields: tuple[Literal["commitment_arrival", "answer_arrival"], ...]

    @field_validator("bias", mode="before")
    @classmethod
    def _duration(cls, value):
        if isinstance(value, str) and value.strip().startswith("-"):
            return -int(parse_duration_ps(value.strip()[1:]) or 0)
        return parse_duration_ps(value)


class SelectiveJammingAttackConfig(StrictModel):
    type: Literal["selective_jamming"]
    id: str = "selective-jamming"
    link_ids: tuple[str, ...] = ()
    message_types: tuple[str, ...] = ()
    start: Duration = 0
    end: Duration | None = None
    drop_probability: float = Field(default=0, ge=0, le=1)
    added_delay: Duration = 0
    quantum: bool = False

    @field_validator("start", "end", "added_delay", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


class InterceptResendAttackConfig(StrictModel):
    type: Literal["intercept_resend"]
    id: str = "intercept-resend"
    position_m: float
    basis_strategy: Literal["random", "z_only", "x_only"] = "random"
    processing_latency: Duration = "500 ns"
    preparation_latency: Duration = "100 ns"
    replacement_source_fidelity: float = Field(default=1, ge=0.25, le=1)

    @field_validator("processing_latency", "preparation_latency", mode="before")
    @classmethod
    def _duration(cls, value):
        return parse_duration_ps(value)


AttackConfig = Annotated[
    ScheduleSkewAttackConfig
    | TelemetryPoisoningAttackConfig
    | TimestampForgeryAttackConfig
    | SelectiveJammingAttackConfig
    | InterceptResendAttackConfig,
    Field(discriminator="type"),
]


class OutputConfig(StrictModel):
    directory: str = "runs/qpv"
    trace_level: Literal["none", "summary", "full"] = "full"
    write_round_csv: bool = True
    write_event_ndjson: bool = True


class QOrchSimConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    simulation: SimulationConfig
    execution: ExecutionConfig = ExecutionConfig()
    geometry: GeometryConfig
    hardware: HardwareConfig
    links: LinksConfig
    protocol: ProtocolConfig
    controller: ControllerConfig = ControllerConfig()
    attacks: tuple[AttackConfig, ...] = ()
    output: OutputConfig = OutputConfig()

    @model_validator(mode="after")
    def _semantic(self):
        nodes = set(self.geometry.nodes)
        required = {"controller", "v0", "v1", "prover"}
        if missing := sorted(required - nodes):
            raise ValueError(f"missing required nodes: {missing}")
        for link in (*self.links.quantum, *self.links.classical):
            if link.source not in nodes or link.destination not in nodes:
                raise ValueError(f"link {link.id} references unknown endpoint")
        if self.protocol.minimum_committed_rounds > self.simulation.rounds:
            raise ValueError("minimum_committed_rounds exceeds rounds")
        required_pairs = {
            ("v0", "prover"),
            ("v1", "prover"),
            ("prover", "v0"),
            ("prover", "v1"),
            ("v0", "controller"),
            ("v1", "controller"),
        }
        pairs = {(link.source, link.destination) for link in self.links.classical}
        if missing_pairs := sorted(required_pairs - pairs):
            raise ValueError(f"missing directional classical links: {missing_pairs}")
        return self
