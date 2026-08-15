"""Immutable QPV round plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from qorchsim.network.geometry import Position


@dataclass(frozen=True, slots=True)
class RoundPlan:
    session_id: str
    round_id: str
    round_index: int
    nonce: str
    telemetry_epoch: int
    challenge_send_ps: int
    x_send_ps: int
    y_send_ps: int
    commitment_deadline_by_verifier: Mapping[str, int]
    answer_deadline_by_verifier: Mapping[str, int]
    expected_prover_position: Position
    maximum_authenticated_radius_m: float
    physical_attack_ids: tuple[str, ...] = ()
    controller_expected_original: bool = False
