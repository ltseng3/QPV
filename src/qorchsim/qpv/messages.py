"""Immutable protocol messages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    CAPABILITY_REPORT = "capability_report"
    ROUND_PLAN = "round_plan"
    BASIS_INPUT_X = "basis_input_x"
    BASIS_INPUT_Y = "basis_input_y"
    COMMITMENT = "commitment"
    ANSWER = "answer"
    VERIFIER_REPORT = "verifier_report"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class ProtocolMessage:
    schema_version: str
    message_type: MessageType
    session_id: str
    round_id: str | None
    sender_id: str
    receiver_id: str
    nonce: str
    telemetry_epoch: int
    payload: Any
    authentic: bool = True
