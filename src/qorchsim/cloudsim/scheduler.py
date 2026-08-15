"""Scheduler interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qorchsim.cloudsim.allocations import Allocation
from qorchsim.cloudsim.resources import ResourceSnapshot
from qorchsim.cloudsim.workloads import Workload


@dataclass(frozen=True, slots=True)
class SchedulingDecision:
    accepted: bool
    allocation: Allocation | None
    reason_codes: tuple[str, ...] = ()


class SchedulerPolicy(Protocol):
    def schedule(self, workload: Workload, resources: ResourceSnapshot, now_ps: int) -> SchedulingDecision: ...
