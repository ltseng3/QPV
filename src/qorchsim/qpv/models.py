"""QPV state, telemetry, and result values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProverRoundState(str, Enum):
    WAITING_FOR_CHALLENGE = "waiting_for_challenge"
    QND_IN_PROGRESS = "qnd_in_progress"
    MEMORY_LOADING = "memory_loading"
    COMMITTED_WITH_STATE = "committed_with_state"
    COMMITTED_WITHOUT_STATE = "committed_without_state"
    WAITING_FOR_BASIS = "waiting_for_basis"
    MEMORY_RETRIEVING = "memory_retrieving"
    MEASURING = "measuring"
    ANSWER_SENT = "answer_sent"
    NO_COMMITMENT = "no_commitment"
    ABORTED = "aborted"
    COMPLETE = "complete"


class VerifierRoundState(str, Enum):
    PLANNED = "planned"
    PREPARING = "preparing"
    CHALLENGE_SENT = "challenge_sent"
    BASIS_SENT = "basis_sent"
    COMMITMENT_RECEIVED = "commitment_received"
    LOCAL_MEASUREMENT_COMPLETE = "local_measurement_complete"
    ANSWER_RECEIVED = "answer_received"
    REPORT_SENT = "report_sent"
    ABORTED = "aborted"
    COMPLETE = "complete"


class ControllerRoundState(str, Enum):
    CALIBRATING = "calibrating"
    PLANNING = "planning"
    PLAN_DISTRIBUTED = "plan_distributed"
    COLLECTING_REPORTS = "collecting_reports"
    DECIDING = "deciding"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    node_id: str
    telemetry_epoch: int
    observed_at_ps: int
    reported_capabilities: dict[str, object]
    authentic: bool = True


@dataclass(frozen=True, slots=True)
class VerifierReport:
    session_id: str
    round_id: str
    verifier_id: str
    nonce: str
    telemetry_epoch: int
    commitment: int | None
    answer: int | None
    local_measurement: int | None
    commitment_physical_ps: int | None
    commitment_local_ps: int | None
    commitment_reported_ps: int | None
    answer_physical_ps: int | None
    answer_local_ps: int | None
    answer_reported_ps: int | None
    commitment_deadline_ps: int
    answer_deadline_ps: int
    authentic: bool = True
    attack_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    accepted: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoundResult:
    session_id: str
    round_id: str
    round_index: int
    committed: bool
    valid_state_commitment: bool
    qnd_outcome: str
    prover_measurement: int | None
    verifier_measurement: int | None
    measurement_match: bool | None
    memory_dwell_ps: int | None
    commitment_physical_margin_ps: int | None
    commitment_controller_margin_ps: int | None
    v0_response_physical_margin_ps: int | None
    v0_response_reported_margin_ps: int | None
    v1_response_physical_margin_ps: int | None
    v1_response_reported_margin_ps: int | None
    accepted: bool
    reason_codes: tuple[str, ...]
    attack_ids: tuple[str, ...] = ()
    prover_position_m: float = 0.0


@dataclass(frozen=True, slots=True)
class SessionResult:
    session_id: str
    rounds: tuple[RoundResult, ...]
    accepted: bool
    committed_rounds: int
    valid_committed_rounds: int
    outcome_mismatches: int
    timing_violations: int
    qber: float
    reason_codes: tuple[str, ...]
