# Tutorial 4: Extending Toward a CloudSim-Style Simulator

Version 1 already runs QPV through portable workload, resource, scheduling, allocation,
and execution interfaces. This tutorial shows how to add a scheduler without importing
SeQUeNCe or QPV device runtime classes.

## 1. Implement a policy

```python
from qorchsim.cloudsim.allocations import Allocation
from qorchsim.cloudsim.scheduler import SchedulingDecision
from qorchsim.core.identifiers import stable_id


class TrustAwareScheduler:
    def __init__(self, minimum_trust: float = 0.9) -> None:
        self.minimum_trust = minimum_trust

    def schedule(self, workload, resources, now_ps):
        participants = tuple(workload.parameters.get("participants", ()))
        nodes = {node.node_id: node for node in resources.nodes}

        missing = sorted(set(participants) - set(nodes))
        if missing:
            return SchedulingDecision(False, None, (f"missing:{','.join(missing)}",))

        untrusted = sorted(
            node_id for node_id in participants
            if nodes[node_id].trust < self.minimum_trust
        )
        if untrusted:
            return SchedulingDecision(False, None, (f"untrusted:{','.join(untrusted)}",))

        allocation = Allocation(
            allocation_id=stable_id(
                "trust-allocation", workload.workload_id, resources.telemetry_epoch
            ),
            workload_id=workload.workload_id,
            node_bindings={node_id: node_id for node_id in participants},
            device_bindings={r.resource_id: r.resource_id for r in resources.devices},
            link_bindings={r.resource_id: r.resource_id for r in resources.links},
            start_time_ps=max(now_ps, workload.arrival_time_ps),
            end_time_ps=workload.deadline_ps or 2**63 - 1,
        )
        return SchedulingDecision(True, allocation)
```

The policy receives immutable scheduler-visible snapshots. It does not see live memory
objects, density matrices, event queues, or SeQUeNCe components.

## 2. Test it as a pure unit

```python
from qorchsim.cloudsim.resources import NodeResource, ResourceSnapshot
from qorchsim.cloudsim.workloads import Workload

snapshot = ResourceSnapshot(
    observed_at_ps=0,
    nodes=(
        NodeResource("v0", (-1000.0, 0.0), trust=1.0),
        NodeResource("prover", (0.0, 0.0), trust=0.5),
    ),
    devices=(),
    links=(),
    telemetry_epoch=1,
)
workload = Workload(
    workload_id="job-1",
    workload_type="qpv",
    arrival_time_ps=0,
    deadline_ps=1_000_000,
    priority=0,
    parameters={"participants": ("v0", "prover")},
)

result = TrustAwareScheduler().schedule(workload, snapshot, 0)
assert not result.accepted
assert result.reason_codes == ("untrusted:prover",)
```

## 3. Future queueing layer

A later workload broker can hold immutable `Workload` values in states such as pending,
admitted, running, completed, failed, and preempted. It can call any `SchedulerPolicy`
and submit accepted allocations to one of several `ExecutionModel` implementations:

```text
analytical execution   -> sampled completion/fidelity
stochastic execution   -> component-level random outcomes
detailed execution     -> SeQUeNCe-backed protocol events
```

The scheduler and attack interfaces remain unchanged across these fidelity levels.

## 4. Resource and attack interaction

Inventory attacks run before scheduling. This enables experiments on stale or forged
resource information without modifying scheduler implementations:

```text
physical inventory -> attack pipeline -> scheduler-visible snapshot -> policy
```

A trust-aware or freshness-aware policy can be compared against first-fit under the
same attacked snapshot and workload arrival stream.
