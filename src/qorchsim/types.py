"""Strong aliases and basic result enums."""

from enum import Enum
from typing import NewType

SimTimePs = NewType("SimTimePs", int)
DurationPs = NewType("DurationPs", int)
NodeId = NewType("NodeId", str)
RoundId = NewType("RoundId", str)
SessionId = NewType("SessionId", str)
ResourceId = NewType("ResourceId", str)
TransmissionId = NewType("TransmissionId", str)


class OperationStatus(str, Enum):
    """Expected operation outcomes."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"
    ABORTED = "aborted"
