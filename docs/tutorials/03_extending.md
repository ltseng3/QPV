# Tutorial 3: Extending QOrchSim

## Add an attack

Subclass `IdentityAttack` and override only the relevant hook:

```python
from qorchsim.attacks.base import IdentityAttack

class DuplicateCommitmentAttack(IdentityAttack):
    attack_id = "duplicate-commitment"

    def alter_classical(self, tx, ctx):
        if tx.message_type != "commitment":
            return (tx,)
        replay = tx.with_attack(self.attack_id, added_delay_ps=tx.added_delay_ps + 1_000_000)
        return (tx, replay)
```

Register a Pydantic attack configuration and construct it in
`qorchsim.experiments.runner._attack_pipeline`.

## Add a scheduling policy

Implement the portable `SchedulerPolicy` interface:

```python
class FidelityAwareScheduler:
    def schedule(self, workload, resources, now_ps):
        # Filter hard constraints, score feasible allocations, return one decision.
        ...
```

The scheduler must only see `ResourceSnapshot`, never device runtime objects.

## Add an execution model

Implement `ExecutionModel.submit()`. A future analytical model can return sampled
completion events without evolving density matrices, while using the same workload,
attack, and metric packages.
