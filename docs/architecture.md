# QOrchSim Architecture

QOrchSim is a deterministic, modular simulator for commitment-based quantum position
verification security. Version 1 uses SeQUeNCe for virtual time and quantum-state
storage when the `sequence_qpv` backend is selected, but all scientific models are
expressed through portable Python interfaces.

## Dependency rule

```text
CLI / YAML / persistence
          |
          v
experiment runner and sweep engine
          |
          v
CloudSim-style workload + scheduler + allocation
          |
          v
QPV protocol runtime, attacks, policies, metrics
          |
          v
scheduler and quantum-operation ports
        /   \
       /     \
portable      SeQUeNCe 1.0.0 adapter
backend       timeline + density manager
```

Only `qorchsim.adapters.sequence` may import `sequence.*`. This is enforced by code
review and an import audit. The boundary makes protocol tests fast and preserves a
future path to analytical, stochastic, or alternate detailed execution backends.

## Package responsibilities

| Package | Responsibility |
|---|---|
| `core` | deterministic events, priorities, clock port, event bus, identifiers, named RNG streams |
| `config` | strict YAML schema, duration normalization, semantic validation |
| `quantum` | portable density-matrix states, EPR/BB84 operations, Kraus channels, noise models |
| `devices` | explicit timed EPR source, QND detector, memory, measurement, local clock |
| `network` | geometry, directional links, immutable transmission envelopes, arrival timing |
| `qpv` | round plans, messages, participant state, complete session execution and acceptance |
| `attacks` | ordered transforms at inventory, plan, classical, quantum, report, and result stages |
| `policies` | schedule, telemetry, freshness, and acceptance checks |
| `cloudsim` | workload, resource snapshot, scheduler, allocation, and execution interfaces |
| `metrics` | round records, timing summaries, security summaries, utilization helpers |
| `tracing` | streaming NDJSON events and run manifests |
| `experiments` | single runs, sweeps, process parallelism, persisted summaries |
| `adapters.sequence` | SeQUeNCe version guard, event pump, timeline scheduler, quantum manager adapter |

## Timing model

All physical time is an integer number of picoseconds. Domain code never calls wall
clock APIs. Events are ordered by time, then a security-relevant phase, then a monotonic
sequence value.

```text
PHYSICAL_ARRIVAL
DEVICE_COMPLETION
PROTOCOL_REACTION
CONTROLLER_ACTION
TIMEOUT
OBSERVABILITY
```

This order prevents a heap implementation from deciding whether a response at exactly
the deadline is accepted. Each boundary is explicit and testable.

Three timestamps are carried separately:

- **physical time**: ground-truth event time on the simulator timeline;
- **local time**: node clock after offset, drift, and jitter;
- **reported time**: value placed in telemetry after any forgery attack.

Schedule-skew attacks change physical transmission events. Timestamp-forgery attacks
change only reported values. Tests assert that distinction.

## SeQUeNCe adapter

The adapter has two essential responsibilities:

1. `SequenceEventScheduler` maps portable scheduled callbacks to SeQUeNCe `Event` and
   `Process` objects while encoding stable event phase and sequence order.
2. `SequenceQuantumOperations` stores states in SeQUeNCe's density-matrix manager and
   implements the same `QuantumOperations` contract used by the portable backend.

QPV devices, attacks, and protocol state machines do not subclass framework classes.
This avoids coupling their scientific behavior to a particular release and makes
contract tests possible without the external package.

The binding modules under `adapters.sequence` define the future direct-node,
direct-channel, device, and protocol bridge seams. They contain no version-1 placeholder
execution behavior.

## Quantum state model

The version-1 protocol involves small states, so exact density matrices are used.
Supported operations include:

- Bell-pair creation;
- BB84 `Z` and `X` preparation and measurement;
- source depolarization;
- subsystem amplitude damping and dephasing;
- measurement error;
- intercept-measure-resend on the actual challenge qubit;
- Bell-state fidelity checks.

Timed memory devices record completed load time and apply noise for the actual storage
interval at retrieval. The state does not become resident merely because a request was
issued.

## Device state machines

Every physical component validates transitions. Representative flows are:

```text
EPR source: IDLE -> GENERATING -> IDLE
QND:        IDLE -> ACTIVE -> DEAD_TIME -> IDLE
Memory:     EMPTY -> LOADING -> OCCUPIED -> RETRIEVING -> EMPTY
Measurement:IDLE -> SWITCHING -> MEASURING -> DEAD_TIME -> IDLE
```

Invalid concurrent operations raise typed errors during development rather than
silently changing state.

## QPV session execution

For each round:

1. The controller creates a nonce-bound plan.
2. `v0` schedules Bell-pair generation.
3. The challenge qubit and basis messages are transmitted on directional links.
4. The prover performs QND presence detection and memory loading.
5. Commitment messages are sent after a valid completed presence/load sequence.
6. When both basis bits arrive, memory retrieval and BB84 measurement are scheduled.
7. `v0` measures its retained qubit in the same basis.
8. Verifiers timestamp reports and send them to the controller.
9. The controller evaluates physical and inferred timing, freshness, result agreement,
   and policy constraints.
10. Round results feed session QBER and acceptance.

All waiting intervals are timeline events; no operation is represented by a blocking
sleep.

## Attack pipeline

Attacks are ordered immutable transforms:

```text
physical inventory -> alter_inventory
round plan          -> alter_plan
classical send      -> alter_classical
quantum send        -> decide_quantum_send
verifier report     -> alter_report
round/session result-> alter_result
```

An attack may return replacement immutable values, drop a transmission, or duplicate a
classical transmission. It does not reach into unrelated protocol state. This keeps
attack composition auditable and lets future CloudSim-style workloads reuse inventory,
network, and result attacks.

## CloudSim extension seam

Version 1 already models QPV as:

```text
Workload
  -> SchedulerPolicy(ResourceSnapshot)
  -> SchedulingDecision + Allocation
  -> ExecutionModel.submit()
  -> ExecutionHandle
```

The current `StaticQpvScheduler` performs one gang allocation. Future additions can
introduce workload arrivals, queues, reservation calendars, contention, preemption,
trust-aware or fidelity-aware policies, and multiple execution fidelities without
changing the QPV protocol.

The critical rule is that a scheduler sees immutable `ResourceSnapshot` values, not
live devices or quantum states. Telemetry-poisoning attacks therefore alter what a
scheduler sees while physical devices continue using ground-truth capabilities.

## Persistence and reproducibility

Successful runs are written atomically and include:

- `manifest.json`: normalized configuration, seed, versions, warnings, event count;
- `events.ndjson`: appendable canonical event trace;
- `rounds.csv`: stable one-row-per-round data;
- `summary.json`: security and timing aggregates.

Randomness comes from deterministic named streams derived from one master seed. Adding
a random draw to one component does not perturb unrelated components that use different
stream names.

## Failure behavior

Configuration and invariant errors fail loudly. The experiment runner closes the trace,
writes the exception and manifest, and atomically retains a `.failed` directory. Normal
protocol failures—loss, timeout, rejected plan, or mismatched result—are modeled as
explicit result states rather than Python exceptions.
