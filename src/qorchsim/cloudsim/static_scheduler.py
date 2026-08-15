"""Static scheduler used by version 1 QPV workloads."""

from __future__ import annotations

from qorchsim.cloudsim.allocations import Allocation
from qorchsim.cloudsim.resources import ResourceSnapshot
from qorchsim.cloudsim.scheduler import SchedulingDecision
from qorchsim.cloudsim.workloads import Workload
from qorchsim.core.identifiers import stable_id


class StaticQpvScheduler:
    """Validate configured nodes/resources and return a fixed gang allocation."""

    def schedule(self, workload: Workload, resources: ResourceSnapshot, now_ps: int) -> SchedulingDecision:
        required_nodes = tuple(str(node) for node in workload.parameters.get("participants", ()))
        available = {node.node_id for node in resources.nodes}
        missing = sorted(set(required_nodes) - available)
        if missing:
            return SchedulingDecision(False, None, (f"missing_nodes:{','.join(missing)}",))
        allocation = Allocation(
            allocation_id=stable_id("allocation", workload.workload_id, resources.telemetry_epoch),
            workload_id=workload.workload_id,
            node_bindings={node: node for node in required_nodes},
            device_bindings={device.resource_id: device.resource_id for device in resources.devices},
            link_bindings={link.resource_id: link.resource_id for link in resources.links},
            start_time_ps=max(now_ps, workload.arrival_time_ps),
            end_time_ps=workload.deadline_ps or 2**63 - 1,
        )
        return SchedulingDecision(True, allocation)
