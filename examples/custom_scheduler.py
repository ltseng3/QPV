"""Pure-Python CloudSim-style scheduler extension example."""

from __future__ import annotations

from qorchsim.cloudsim.allocations import Allocation
from qorchsim.cloudsim.resources import NodeResource, ResourceSnapshot
from qorchsim.cloudsim.scheduler import SchedulingDecision
from qorchsim.cloudsim.workloads import Workload
from qorchsim.core.identifiers import stable_id


class TrustAwareScheduler:
    """Gang-allocate a workload only when every participant is trusted."""

    def __init__(self, minimum_trust: float = 0.9) -> None:
        self.minimum_trust = minimum_trust

    def schedule(
        self,
        workload: Workload,
        resources: ResourceSnapshot,
        now_ps: int,
    ) -> SchedulingDecision:
        participants = tuple(str(node) for node in workload.parameters.get("participants", ()))
        nodes = {node.node_id: node for node in resources.nodes}
        missing = sorted(set(participants) - set(nodes))
        if missing:
            return SchedulingDecision(False, None, (f"missing:{','.join(missing)}",))
        untrusted = sorted(
            node_id for node_id in participants if nodes[node_id].trust < self.minimum_trust
        )
        if untrusted:
            return SchedulingDecision(False, None, (f"untrusted:{','.join(untrusted)}",))
        allocation = Allocation(
            allocation_id=stable_id("trust-allocation", workload.workload_id),
            workload_id=workload.workload_id,
            node_bindings={node_id: node_id for node_id in participants},
            device_bindings={},
            link_bindings={},
            start_time_ps=max(now_ps, workload.arrival_time_ps),
            end_time_ps=workload.deadline_ps or 2**63 - 1,
        )
        return SchedulingDecision(True, allocation)


def main() -> None:
    resources = ResourceSnapshot(
        observed_at_ps=0,
        nodes=(
            NodeResource("v0", (-1_000.0, 0.0), trust=1.0),
            NodeResource("prover", (0.0, 0.0), trust=0.6),
        ),
        devices=(),
        links=(),
        telemetry_epoch=1,
    )
    workload = Workload(
        workload_id="qpv-job-1",
        workload_type="commitment_qpv",
        arrival_time_ps=0,
        deadline_ps=100_000_000,
        priority=0,
        parameters={"participants": ("v0", "prover")},
    )
    print(TrustAwareScheduler().schedule(workload, resources, now_ps=0))


if __name__ == "__main__":
    main()
