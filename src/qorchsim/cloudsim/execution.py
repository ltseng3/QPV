"""Execution-model interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qorchsim.cloudsim.allocations import Allocation
from qorchsim.cloudsim.workloads import Workload


@dataclass(frozen=True, slots=True)
class ExecutionHandle:
    execution_id: str
    workload_id: str


class ExecutionModel(Protocol):
    def submit(self, workload: Workload, allocation: Allocation) -> ExecutionHandle: ...
