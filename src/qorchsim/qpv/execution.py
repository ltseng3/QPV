"""QPV execution model bridging CloudSim-style workloads to the runtime."""

from __future__ import annotations

from qorchsim.cloudsim.allocations import Allocation
from qorchsim.cloudsim.execution import ExecutionHandle
from qorchsim.cloudsim.workloads import Workload
from qorchsim.core.identifiers import stable_id
from qorchsim.qpv.session import QpvSessionRuntime


class QpvExecutionModel:
    """Submit one statically allocated QPV workload to its event runtime."""

    def __init__(self, runtime: QpvSessionRuntime) -> None:
        self.runtime = runtime

    def submit(self, workload: Workload, allocation: Allocation) -> ExecutionHandle:
        self.runtime.schedule()
        return ExecutionHandle(stable_id("execution", workload.workload_id, allocation.allocation_id), workload.workload_id)
