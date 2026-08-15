# QOrchSim Technical Software Specification

**Document status:** Implementation-ready specification  
**Version:** 1.0  
**Target implementation:** Python 3.12, SeQUeNCe 1.0.0  
**Primary use case:** Security evaluation of SDN-orchestrated commitment-based quantum position verification (QPV)  
**Extension goal:** Evolve into a CloudSim-style discrete-event simulator for quantum-network resource scheduling and coordination

---

## 1. Executive Summary

QOrchSim is a modular discrete-event simulation framework for studying the security and operational behavior of quantum-network applications. Version 1 focuses on a two-verifier, commitment-based QPV protocol and evaluates attacks on its quantum–classical timing envelope, resource telemetry, control messages, and network availability.

The simulator uses SeQUeNCe as its virtual-time and quantum-state execution backend. QOrchSim must not expose SeQUeNCe classes as its domain API. QPV protocol logic, attack models, security policies, workload descriptions, resource views, metrics, and experiment definitions must remain simulator-independent plain Python. A narrow adapter translates those models into SeQUeNCe entities, events, photons, channels, and quantum-manager operations.

This separation serves two goals:

1. Produce a rigorous, physics-aware QPV security simulator suitable for the current paper.
2. Preserve a clean path toward a future CloudSim-like simulator with workload arrivals, resource scheduling, reservations, contention, multi-tenancy, and alternative execution models.

Version 1 will implement:

- deterministic picosecond virtual time;
- explicit quantum and classical protocol event ordering;
- EPR-pair creation and BB84-basis measurements;
- lossy quantum channels and delayed classical channels;
- a custom quantum non-demolition (QND) presence-detector abstraction;
- timed quantum-memory loading, storage noise, retrieval, and expiration;
- timed measurement operations;
- physical, local-clock, and reported timestamps;
- a complete multi-round QPV session state machine;
- five attacks: schedule skew, telemetry poisoning, timestamp forgery, selective jamming, and intercept–measure–resend;
- baseline and security-aware control policies;
- reproducible Monte Carlo experiments and parameter sweeps;
- event traces, round-level results, session summaries, and security metrics;
- a minimal workload/resource/scheduler abstraction for future CloudSim-style expansion.

Version 1 will not implement a real Kubernetes system, real QNodeOS integration, full Byzantine consensus, arbitrary entanglement-assisted adversaries, optical wave-packet simulation, or a general-purpose packet-network stack.

---

## 2. Source and API Baseline

The implementation must pin the following baseline:

```toml
python = ">=3.12,<3.15"
sequence = "==1.0.0"
```

The design relies on these SeQUeNCe 1.0.0 behaviors:

- `Timeline` stores integer picosecond time, executes events from a heap, and stops before an event whose time is equal to or greater than `stop_time`.
- `Event` ordering is based on numeric `time` and numeric `priority`; lower values run first.
- `Process` invokes a named method on an owner object.
- `QuantumChannel` derives propagation delay from distance and light speed, applies attenuation-based loss, supports a maximum transmission frequency, and schedules `receive_qubit` at the destination.
- `ClassicalChannel` schedules lossless message delivery using channel delay plus an optional sender delay.
- `Detector` models efficiency, dark-count rate, count-rate dead time, and timestamp resolution.
- `Photon` can use the timeline quantum manager and polarization encoding.
- `QuantumManagerDensity` supports composite density matrices, circuits, measurement, state retrieval, and state replacement.
- `Node` dispatches classical messages to protocols and forwards incoming qubits to a configured first component.

The code must isolate all assumptions about these APIs in `qorchsim.adapters.sequence`. No other package may import `sequence.*`.

### 2.1 Reference sources

- SeQUeNCe repository: <https://github.com/sequence-toolbox/SeQUeNCe>
- SeQUeNCe documentation: <https://sequence-rtd-tutorial.readthedocs.io/>
- SeQUeNCe `Timeline`: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/kernel/timeline.py>
- SeQUeNCe `Event`: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/kernel/event.py>
- SeQUeNCe optical channels: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/components/optical_channel.py>
- SeQUeNCe detector models: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/components/detector.py>
- SeQUeNCe memory models: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/components/memory.py>
- SeQUeNCe photon model: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/components/photon.py>
- SeQUeNCe quantum manager: <https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/sequence/kernel/quantum_manager.py>
- SDN-enabled QPV paper: <https://ziyanzhang98.github.io/_pages/SDN_enabled_Quantum_Position_Verification.pdf>

---

## 3. Product Goals

### 3.1 Primary goals

1. **Timing correctness**  
   Every security-relevant action must occur at an explicit virtual timestamp. Waiting must affect quantum state when applicable.

2. **Physical-versus-observed separation**  
   The simulator must separately represent physical ground-truth time, a node's local clock, and a potentially forged reported timestamp.

3. **Quantum-essential evaluation**  
   At least two evaluated attacks must change actual quantum behavior rather than only classical controller state. Schedule skew and memory-capability falsification satisfy this requirement.

4. **Attack extensibility**  
   New attacks must be addable without modifying the QPV protocol state machines or SeQUeNCe kernel.

5. **Policy extensibility**  
   Baseline and defended controller policies must share the same protocol and execution model.

6. **Reproducibility**  
   A normalized configuration, seed, package versions, and source revision must reproduce the same event trace.

7. **CloudSim-style evolution**  
   The initial QPV session must execute through generic workload, resource, allocation, and execution interfaces that can later support queues, schedulers, reservations, and other quantum applications.

### 3.2 Secondary goals

- Human-readable YAML configuration.
- Command-line execution and parameter sweeps.
- Structured event traces suitable for post-processing.
- Unit-testable domain logic without SeQUeNCe.
- Component validation against analytical calculations.
- Reasonable performance for thousands of protocol rounds and tens to hundreds of Monte Carlo runs per process.

---

## 4. Non-Goals for Version 1

The following are explicitly out of scope:

- real Kubernetes integration;
- real QNodeOS or hardware integration;
- Kubernetes CRDs, operators, reconciliation loops, or DRA drivers;
- full BFT controller replication;
- security proofs against arbitrary quantum adversaries;
- unlimited or large-scale preshared-entanglement attacks;
- arbitrary POVM optimization;
- temporal-mode, wave-packet, or beam-propagation simulation;
- detailed electromagnetic or wireless interference models;
- TCP/IP, MAC, transport, congestion-control, or routing-protocol simulation;
- multi-verifier Byzantine quorum geometry beyond a simple extension interface;
- full optical implementation of a QND detector;
- graphical user interface;
- distributed simulation across machines;
- automatic calibration from laboratory data.

These exclusions are deliberate. Version 1 must be a complete, reliable QPV security simulator, not a partial implementation of a broader platform.

---

## 5. Scientific Scope and Protocol Assumptions

### 5.1 Topology

Version 1 models a one-dimensional or two-dimensional topology with these logical participants:

- controller `C`;
- verifier `V0` with an EPR source and retained quantum memory;
- verifier `V1` supplying the second classical basis input;
- claimed prover position `P*`;
- actual prover `P`;
- optional quantum interceptor `A`.

The default physical arrangement is one-dimensional:

```text
V0 ---------------- P* ---------------- V1
```

The simulator must accept arbitrary Cartesian coordinates and derive link distances from coordinates unless the configuration supplies an explicit link length.

### 5.2 Protocol round

A round uses a simplified commitment-based, entanglement-assisted BB84 QPV protocol:

1. The controller issues a `RoundPlan` containing round identifier, nonce, participants, send times, deadlines, and expected timing bounds.
2. `V0` creates an EPR pair in the state

   \[
   |\Phi^+\rangle = (|00\rangle + |11\rangle)/\sqrt 2.
   \]

3. `V0` retains one qubit and transmits the challenge qubit toward `P`.
4. `V0` and `V1` send uniformly random bits `x` and `y` such that they should reach `P*` after the challenge by configured delay `delta`.
5. The prover performs QND presence detection. On a valid detection, it loads the challenge state into memory and broadcasts commitment `c=1`. If no detection occurs before the gate closes, it sends `c=0`.
6. Once both `x` and `y` are available, the prover computes basis bit

   \[
   b = f(x,y) = x \oplus y.
   \]

7. The prover retrieves the stored qubit and measures it in `Z` basis for `b=0` or `X` basis for `b=1`, producing result `a`.
8. `V0` measures its retained qubit in the same basis, producing result `v`.
9. The prover sends `a` to both verifiers.
10. Each verifier creates a signed-model report containing local timestamps, reported timestamps, commitment, answer, deadline checks, and observations.
11. The controller applies the selected acceptance policy.

### 5.3 Multi-round session

A `QpvSession` contains `N` rounds. A session result must include:

- total rounds;
- committed rounds;
- valid committed rounds;
- outcome mismatches;
- timing violations;
- replay/freshness violations;
- aborted rounds;
- conditional quantum bit error rate;
- final accept/reject decision.

The default acceptance policy is configurable but must support:

```text
committed_rounds >= minimum_committed_rounds
qber <= maximum_qber
all critical freshness checks pass
number of timing violations <= maximum_timing_violations
```

The simulator evaluates specified attacks. It must not claim general cryptographic security from simulation results.

---

## 6. Architectural Principles

### 6.1 Dependency rule

The project uses a strict inward dependency rule:

```text
CLI / adapters / persistence
          ↓
application services / experiments
          ↓
domain models / policies / attacks / metrics
```

Only `qorchsim.adapters.sequence` may import SeQUeNCe. The domain layer must be runnable under unit tests without installing or initializing a SeQUeNCe timeline.

### 6.2 Composition over inheritance

- Domain attacks are composed into attack pipelines.
- Security policies are injected into the controller.
- Device capabilities are immutable configuration objects; device runtime state is separate.
- SeQUeNCe subclasses are limited to integration objects that require framework inheritance.
- Protocol state machines use explicit state objects rather than long inheritance chains.

### 6.3 Explicit state machines

Every stateful device and protocol must use an enum-backed state machine with validated transitions. Silent or ad hoc state changes are prohibited.

### 6.4 Immutable messages and plans

Controller plans, telemetry records, protocol messages, resource snapshots, and results must be immutable domain values. An attack creates a replacement value rather than mutating an object in place.

### 6.5 No hidden time or randomness

- Domain code must not call `time.time`, `datetime.now`, or `random.*`.
- Domain code receives time through `SimulationClock`.
- Randomness comes from named streams supplied by `RandomStreams`.
- All physical time is integer picoseconds.

### 6.6 Fail loudly

Invalid state transitions, events scheduled in the past, duplicate resource allocation, unknown round identifiers, inconsistent nonces, or impossible device operations must raise typed exceptions during development and tests. Expected protocol failures must be returned as explicit result states rather than exceptions.

---

## 7. High-Level Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│ CLI and Experiment Runner                                     │
│ validate, run, sweep, summarize                               │
├───────────────────────────────────────────────────────────────┤
│ Application Services                                          │
│ scenario builder, session service, experiment service         │
├───────────────────────────────────────────────────────────────┤
│ CloudSim-Compatible Domain Core                               │
│ workloads, resources, allocations, scheduler, execution model │
├───────────────────────────────────────────────────────────────┤
│ QPV Domain                                                    │
│ plans, messages, state machines, policies, metrics             │
├───────────────────────────────────────────────────────────────┤
│ Attack and Defense Pipelines                                  │
│ inventory, plan, transmission, report, result hooks           │
├───────────────────────────────────────────────────────────────┤
│ Simulation Ports                                               │
│ clock, scheduler, event bus, quantum operations, trace sink    │
├───────────────────────────────────────────────────────────────┤
│ SeQUeNCe Adapter                                               │
│ Timeline, Event, Process, Node, Channel, Photon, QM            │
├───────────────────────────────────────────────────────────────┤
│ SeQUeNCe 1.0.0                                                │
└───────────────────────────────────────────────────────────────┘
```

---

## 8. Project Layout

```text
qorchsim/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── configs/
│   ├── qpv_ideal.yaml
│   ├── qpv_noisy.yaml
│   ├── attacks/
│   │   ├── schedule_skew.yaml
│   │   ├── telemetry_poisoning.yaml
│   │   ├── timestamp_forgery.yaml
│   │   ├── selective_jamming.yaml
│   │   └── intercept_resend.yaml
│   └── sweeps/
│       ├── skew_vs_memory.yaml
│       └── attack_heatmap.yaml
├── src/qorchsim/
│   ├── __init__.py
│   ├── errors.py
│   ├── types.py
│   │
│   ├── core/
│   │   ├── clock.py
│   │   ├── events.py
│   │   ├── event_bus.py
│   │   ├── random_streams.py
│   │   ├── identifiers.py
│   │   └── lifecycle.py
│   │
│   ├── cloudsim/
│   │   ├── workloads.py
│   │   ├── resources.py
│   │   ├── allocations.py
│   │   ├── scheduler.py
│   │   ├── execution.py
│   │   └── static_scheduler.py
│   │
│   ├── qpv/
│   │   ├── models.py
│   │   ├── messages.py
│   │   ├── plans.py
│   │   ├── session.py
│   │   ├── verifier.py
│   │   ├── prover.py
│   │   ├── controller.py
│   │   ├── basis.py
│   │   ├── acceptance.py
│   │   └── timing.py
│   │
│   ├── devices/
│   │   ├── capabilities.py
│   │   ├── epr_source.py
│   │   ├── qnd_detector.py
│   │   ├── quantum_memory.py
│   │   ├── measurement.py
│   │   └── local_clock.py
│   │
│   ├── quantum/
│   │   ├── operations.py
│   │   ├── kraus.py
│   │   ├── noise.py
│   │   └── states.py
│   │
│   ├── network/
│   │   ├── topology.py
│   │   ├── geometry.py
│   │   ├── transmissions.py
│   │   ├── classical_channel.py
│   │   └── link_state.py
│   │
│   ├── attacks/
│   │   ├── base.py
│   │   ├── pipeline.py
│   │   ├── schedule_skew.py
│   │   ├── telemetry_poisoning.py
│   │   ├── timestamp_forgery.py
│   │   ├── selective_jamming.py
│   │   └── intercept_resend.py
│   │
│   ├── policies/
│   │   ├── freshness.py
│   │   ├── telemetry.py
│   │   ├── schedule.py
│   │   └── security_aware.py
│   │
│   ├── metrics/
│   │   ├── records.py
│   │   ├── timing.py
│   │   ├── security.py
│   │   ├── utilization.py
│   │   └── aggregation.py
│   │
│   ├── tracing/
│   │   ├── events.py
│   │   ├── sink.py
│   │   ├── ndjson.py
│   │   └── manifest.py
│   │
│   ├── config/
│   │   ├── models.py
│   │   ├── loader.py
│   │   ├── validation.py
│   │   └── normalization.py
│   │
│   ├── adapters/
│   │   └── sequence/
│   │       ├── scheduler.py
│   │       ├── event_pump.py
│   │       ├── nodes.py
│   │       ├── protocols.py
│   │       ├── channels.py
│   │       ├── devices.py
│   │       ├── quantum_ops.py
│   │       └── scenario_builder.py
│   │
│   ├── experiments/
│   │   ├── runner.py
│   │   ├── sweep.py
│   │   ├── parallel.py
│   │   └── summary.py
│   │
│   └── cli.py
│
└── tests/
    ├── unit/
    ├── component/
    ├── integration/
    ├── protocol/
    ├── attacks/
    ├── validation/
    ├── regression/
    └── performance/
```

---

## 9. Core Types and Conventions

### 9.1 Time

All physical and simulated durations use integer picoseconds.

```python
from typing import NewType

SimTimePs = NewType("SimTimePs", int)
DurationPs = NewType("DurationPs", int)
```

Conversion functions must be centralized:

```python
def seconds_to_ps(value: float) -> DurationPs:
    """Round to nearest integer picosecond for measured/configured values."""


def causal_seconds_to_ps(value: float) -> DurationPs:
    """Round upward so a physical arrival is never scheduled too early."""
```

Configuration models may accept human-readable units, but normalized domain objects must contain picoseconds only.

### 9.2 Identifiers

Use strongly typed string identifiers:

```python
NodeId = NewType("NodeId", str)
RoundId = NewType("RoundId", str)
SessionId = NewType("SessionId", str)
ResourceId = NewType("ResourceId", str)
TransmissionId = NewType("TransmissionId", str)
```

Identifiers must be deterministic under a fixed session ID and round index where practical.

### 9.3 Event phases

Security-critical same-time ordering must be deterministic. SeQUeNCe does not provide a third FIFO key when time and priority are identical, so QOrchSim must encode phase and sequence into numeric priority.

```python
class EventPhase(IntEnum):
    PHYSICAL_ARRIVAL = 0
    DEVICE_COMPLETION = 10
    PROTOCOL = 20
    CONTROL = 30
    TIMEOUT = 40
    OBSERVABILITY = 90
```

The adapter computes:

```python
SEQUENCE_STRIDE = 1_000_000_000
priority = phase.value * SEQUENCE_STRIDE + same_phase_sequence
```

Rules:

- Physical arrival at a deadline executes before the timeout check.
- Device completion executes before protocol reaction.
- Protocol reaction executes before control-plane aggregation.
- Trace-only events execute last.
- `same_phase_sequence` must be monotonic and less than `SEQUENCE_STRIDE` for a single timestamp and phase.

### 9.4 Result types

Expected failures use explicit result values:

```python
class OperationStatus(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"
    ABORTED = "aborted"
```

Programming errors use typed exceptions in `errors.py`.

---

## 10. Simulation Ports

The domain core depends on interfaces, not SeQUeNCe.

### 10.1 Clock

```python
class SimulationClock(Protocol):
    def now_ps(self) -> SimTimePs: ...
```

### 10.2 Event scheduler

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    payload: object


class EventScheduler(Protocol):
    def schedule_at(
        self,
        when_ps: SimTimePs,
        phase: EventPhase,
        event: DomainEvent,
    ) -> None: ...

    def schedule_after(
        self,
        delay_ps: DurationPs,
        phase: EventPhase,
        event: DomainEvent,
    ) -> None: ...
```

Scheduling an event before `now_ps()` must raise `PastEventError`.

### 10.3 Event bus

```python
class EventHandler(Protocol):
    def handle(self, event: DomainEvent) -> None: ...


class EventBus:
    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
    def publish(self, event: DomainEvent) -> None: ...
```

The event bus must preserve subscription order and reject duplicate handler registration unless explicitly allowed.

### 10.4 Trace sink

```python
class TraceSink(Protocol):
    def append(self, event: "TraceEvent") -> None: ...
    def close(self) -> None: ...
```

### 10.5 Quantum operations

```python
class QuantumOperations(Protocol):
    def create_epr_pair(self, pair_id: str) -> "QuantumPairHandle": ...
    def prepare_bb84(self, qubit: "QuantumHandle", basis: int, bit: int) -> None: ...
    def measure_bb84(self, qubit: "QuantumHandle", basis: int, rng: "Generator") -> int: ...
    def apply_kraus(self, qubit: "QuantumHandle", operators: list[NDArray]) -> None: ...
    def fidelity_to_bell_phi_plus(self, pair: "QuantumPairHandle") -> float: ...
```

This interface allows future analytical or alternative simulator implementations.

---

## 11. SeQUeNCe Adapter Design

### 11.1 Timeline configuration

The adapter creates exactly one `Timeline` per simulation process using density-matrix formalism.

```python
timeline = Timeline(
    stop_time=normalized_config.simulation.stop_time_ps,
    formalism=DENSITY_MATRIX_FORMALISM,
)
```

Constraints:

- All SeQUeNCe entities must be created before `timeline.init()`.
- The stop time must be strictly later than the latest valid event because SeQUeNCe does not execute events at `event.time >= stop_time`.
- Multiple timelines with different quantum-manager formalisms must not run concurrently in the same process because the active formalism is global.
- Parallel Monte Carlo execution must use separate processes, not threads.

### 11.2 Event pump

`Process` invokes a named method, so the adapter uses one SeQUeNCe `Entity` named `QOrchSimEventPump`.

```python
class SequenceEventPump(Entity):
    def init(self) -> None:
        pass

    def dispatch(self, event_id: str) -> None:
        event = self.registry.pop(event_id)
        self.event_bus.publish(event)
```

`SequenceEventScheduler.schedule_at()` stores the immutable `DomainEvent` in the pump registry and schedules:

```python
Event(
    time=when_ps,
    process=Process(event_pump, "dispatch", [event.event_id]),
    priority=encoded_priority,
)
```

The registry must reject duplicate event IDs and must be empty at successful simulation completion except for events beyond stop time explicitly recorded in the manifest.

### 11.3 Nodes

Implement lightweight custom nodes rather than `QuantumRouter` because QPV does not use SeQUeNCe's default entanglement reservation stack.

```python
class SequenceQpvNode(Node):
    # owns protocols, seeded RNG, device adapters, and channel mappings
```

Node types:

- `SequenceControllerNode`
- `SequenceVerifierNode`
- `SequenceProverNode`
- `SequenceInterceptorNode`

Each node must have a deterministic seed from `RandomStreams`.

### 11.4 Protocol bridge

Each QPV participant has a SeQUeNCe `Protocol` bridge. The bridge converts `Message` subclasses to immutable domain messages and calls the domain state machine. Domain state machines never receive a SeQUeNCe node or protocol object.

### 11.5 Classical channels

Implement `AttackableClassicalChannel` as a SeQUeNCe-compatible channel with these features:

- geometry-derived propagation delay;
- optional configured sender processing delay;
- immutable `ClassicalTransmission` envelope;
- attack pipeline invocation;
- zero, one, or multiple resulting deliveries;
- per-delivery added delay;
- message replacement for mutation or replay;
- deterministic priority encoding;
- trace emission at send, attack, drop, and receive.

The stock `ClassicalChannel` is lossless and has no attack pipeline. The custom channel may subclass it but must own its `transmit` implementation.

### 11.6 Quantum channels

Use SeQUeNCe `QuantumChannel` for ordinary propagation, attenuation, polarization noise, and transmit-frequency reservation.

Version 1 quantum-network attacks are modeled as follows:

- send-time skew: alter the source's scheduled send event;
- selective jamming: gate or drop a transmission before calling `QuantumChannel.transmit`;
- intercept–measure–resend: construct explicit links `V0 -> A` and `A -> P`, with an interceptor node processing and retransmitting the state;
- extra forwarding latency: model attacker processing time at `A`.

Do not copy or fork the entire `QuantumChannel.transmit` implementation unless a test demonstrates that composition cannot support a required experiment.

### 11.7 Quantum-manager operations

Use density-matrix formalism. EPR creation is implemented by:

1. Create two `Photon` instances with `use_qm=True` and polarization encoding.
2. Combine their states.
3. Apply a two-qubit circuit containing `H(0)` and `CX(0,1)`.

BB84 measurement must not call `Photon.measure` directly for the X basis while using the quantum manager because the current quantum-manager path performs a Z measurement. Instead:

- for Z basis, run a one-qubit measurement circuit;
- for X basis, run `H` followed by measurement.

### 11.8 Version guard

At startup, the adapter must inspect `importlib.metadata.version("sequence")` and fail unless it is exactly `1.0.0`, unless the user explicitly passes `--allow-unsupported-sequence-version`. Unsupported-version runs must record a warning in the manifest.

---

## 12. Randomness and Reproducibility

### 12.1 Named streams

Use NumPy `SeedSequence` to derive independent streams from one master seed.

Required stream names:

```text
controller
verifier-v0
verifier-v1
prover
source-v0
qnd-prover
memory-v0
memory-prover
measurement-v0
measurement-prover
quantum-link-v0-p
classical-link-v0-p
classical-link-v1-p
attacks/<attack-id>
round/<round-index>
```

`RandomStreams.generator(name)` must return the same stream for the same name within a run and must reject accidental duplicate ownership when requested in strict mode.

### 12.2 Manifest

Each run writes `manifest.json` containing:

- normalized configuration;
- master seed;
- derived run ID;
- QOrchSim version;
- SeQUeNCe version;
- Python version;
- platform information;
- source commit if available;
- start and completion wall-clock timestamps;
- event counts;
- warning list;
- output schema versions.

### 12.3 Determinism requirement

Two runs with the same normalized configuration, seed, package versions, and process architecture must produce byte-identical `events.ndjson`, `rounds.csv`, and `summary.json` after excluding wall-clock metadata.

---

## 13. Resource and Workload Abstractions

These abstractions are deliberately small in version 1. They are the extension seam for the future CloudSim-like simulator.

### 13.1 Workload

```python
@dataclass(frozen=True)
class Workload:
    workload_id: str
    workload_type: str
    arrival_time_ps: SimTimePs
    deadline_ps: SimTimePs | None
    priority: int
    parameters: Mapping[str, object]
```

```python
@dataclass(frozen=True)
class QpvWorkload(Workload):
    session_spec: QpvSessionSpec
```

### 13.2 Resource snapshot

```python
@dataclass(frozen=True)
class ResourceSnapshot:
    observed_at_ps: SimTimePs
    nodes: tuple[NodeResource, ...]
    devices: tuple[DeviceResource, ...]
    links: tuple[LinkResource, ...]
    telemetry_epoch: int
```

The snapshot is what the scheduler sees. It may differ from physical truth under telemetry attacks.

### 13.3 Allocation

```python
@dataclass(frozen=True)
class Allocation:
    allocation_id: str
    workload_id: str
    node_bindings: Mapping[str, NodeId]
    device_bindings: Mapping[str, ResourceId]
    link_bindings: Mapping[str, ResourceId]
    start_time_ps: SimTimePs
    end_time_ps: SimTimePs
```

### 13.4 Scheduler

```python
class SchedulerPolicy(Protocol):
    def schedule(
        self,
        workload: Workload,
        resources: ResourceSnapshot,
        now_ps: SimTimePs,
    ) -> "SchedulingDecision": ...
```

Version 1 implements only `StaticQpvScheduler`, which validates explicitly configured participants and devices and returns a fixed allocation. The interface must not assume static scheduling, allowing future first-fit, fidelity-aware, security-aware, gang, reservation, and preemptive schedulers.

### 13.5 Execution model

```python
class ExecutionModel(Protocol):
    def submit(
        self,
        workload: Workload,
        allocation: Allocation,
    ) -> "ExecutionHandle": ...
```

Version 1 implements `SequenceQpvExecutionModel`. Future implementations may be analytical or stochastic without changing schedulers or attack interfaces.

---

## 14. Device Models

### 14.1 Common device lifecycle

```python
class DeviceState(Enum):
    IDLE = "idle"
    RESERVED = "reserved"
    BUSY = "busy"
    DEGRADED = "degraded"
    FAULTED = "faulted"
```

Each device exposes:

- immutable `DeviceCapabilities`;
- mutable runtime state internal to the device service;
- physical truth telemetry;
- observed telemetry;
- utilization counters;
- explicit operation start and completion events.

### 14.2 EPR source

Capabilities:

```python
@dataclass(frozen=True)
class EprSourceCapabilities:
    generation_latency_ps: DurationPs
    generation_success_probability: float
    pair_fidelity: float
    repetition_rate_hz: float
```

State machine:

```text
IDLE -> GENERATING -> PAIR_READY -> IDLE
                  \-> FAILED -----> IDLE
```

At generation completion:

- sample source success;
- create ideal `|Phi+>` pair;
- apply a configurable source depolarizing channel to reach the requested pair fidelity;
- return a `QuantumPairHandle`.

The source must enforce its repetition-rate and busy constraints.

### 14.3 QND presence detector

The QND detector is an abstract probabilistic component, not an optical circuit simulation.

Capabilities:

```python
@dataclass(frozen=True)
class QndCapabilities:
    operation_latency_ps: DurationPs
    detection_efficiency: float
    dark_count_rate_hz: float
    state_survival_probability: float
    disturbance_probability: float
    dead_time_ps: DurationPs
    gate_width_ps: DurationPs
```

Round behavior:

1. Open a detection gate around the expected challenge arrival.
2. If a photon arrives within the gate and the detector is available, schedule `QND_COMPLETE`.
3. At completion, sample detection efficiency.
4. On successful presence detection, sample survival and disturbance.
5. If the state survives, pass it to the memory load operation.
6. Independently sample whether a dark count occurs within the gate using

   \[
   P_{dc}=1-e^{-\lambda w}.
   \]

7. A dark count can produce a commitment without a valid quantum state.
8. Gate close schedules a no-detection outcome if neither a valid detection nor dark count occurred.

Outcomes:

```python
class QndOutcome(Enum):
    VALID_DETECTION = "valid_detection"
    MISSED_PHOTON = "missed_photon"
    DARK_COUNT = "dark_count"
    STATE_DESTROYED = "state_destroyed"
    OUTSIDE_GATE = "outside_gate"
    DETECTOR_BUSY = "detector_busy"
```

### 14.4 Quantum memory

Implement a custom timed single-qubit memory rather than depending on the entanglement-specific semantics of SeQUeNCe `Memory`.

Capabilities:

```python
@dataclass(frozen=True)
class MemoryCapabilities:
    load_latency_ps: DurationPs
    retrieve_latency_ps: DurationPs
    load_efficiency: float
    retrieve_efficiency: float
    t1_ps: DurationPs | None
    t2_ps: DurationPs | None
    maximum_hold_ps: DurationPs | None
```

State machine:

```text
EMPTY -> LOADING -> STORED -> RETRIEVING -> EMPTY
             |         |          |
             v         v          v
           FAILED    EXPIRED     FAILED
```

Requirements:

- Storage begins at successful load completion, not load request.
- Retrieval releases the qubit at retrieval completion.
- Noise is applied over the interval from load completion through retrieval completion.
- A maximum-hold expiration event is scheduled when applicable.
- Loading or retrieval while not in a valid state raises `InvalidDeviceStateError`.
- Physical capabilities and reported capabilities are separate values.

### 14.5 Memory noise

Use density-matrix Kraus channels.

Amplitude damping for elapsed time `t`:

\[
\gamma = 1-e^{-t/T_1}.
\]

Pure dephasing derives `T_phi` from:

\[
\frac{1}{T_2}=\frac{1}{2T_1}+\frac{1}{T_\phi}.
\]

If only `T2` is supplied, apply a phase-damping channel with coherence multiplier `exp(-t/T2)`. If both are supplied, apply amplitude damping followed by pure dephasing. Configuration validation must reject nonphysical combinations unless the user explicitly selects the simplified model.

To apply a single-qubit channel to a qubit that is part of a composite density matrix:

1. Retrieve the density state and ordered key list.
2. Identify the target subsystem index.
3. Expand each Kraus operator with identity tensors over other subsystems.
4. Compute

   \[
   \rho' = \sum_i K_i \rho K_i^\dagger.
   \]

5. Validate Hermiticity, trace approximately one, and nonnegative eigenvalues within tolerance.
6. Write the resulting state back to all associated keys.

### 14.6 Timed measurement device

Capabilities:

```python
@dataclass(frozen=True)
class MeasurementCapabilities:
    basis_switch_latency_ps: DurationPs
    measurement_latency_ps: DurationPs
    measurement_fidelity: float
    dead_time_ps: DurationPs
```

State changes and quantum measurement occur at operation completion, not request time.

For X-basis measurement, apply `H` then Z measurement. Measurement error is modeled as an optional classical bit flip after the ideal quantum measurement or as a premeasurement depolarizing channel, selected by configuration.

### 14.7 Local clock

```python
@dataclass(frozen=True)
class ClockCapabilities:
    epoch_physical_ps: SimTimePs
    offset_ps: int
    drift_ppm: float
    jitter_stddev_ps: float
    resolution_ps: int
```

Local time:

\[
t_{local}=
\operatorname{quantize}
\left(
 t_0 + (1+\gamma)(t_{physical}-t_0)+\theta+\nu
\right).
\]

The clock produces local observations only. Timestamp-forgery attacks operate on the later reported value.

---

## 15. QPV Domain Model

### 15.1 Round plan

```python
@dataclass(frozen=True)
class RoundPlan:
    session_id: SessionId
    round_id: RoundId
    round_index: int
    nonce: str
    telemetry_epoch: int
    challenge_send_ps: SimTimePs
    x_send_ps: SimTimePs
    y_send_ps: SimTimePs
    commitment_deadline_by_verifier: Mapping[NodeId, SimTimePs]
    answer_deadline_by_verifier: Mapping[NodeId, SimTimePs]
    expected_prover_position: Position
    maximum_authenticated_radius_m: float
```

Plans are immutable. Schedule attacks return a new plan or replace the plan in transit.

### 15.2 Protocol messages

Required message types:

```text
CAPABILITY_REPORT
ROUND_PLAN
BASIS_INPUT_X
BASIS_INPUT_Y
COMMITMENT
ANSWER
VERIFIER_REPORT
ABORT
```

Every message contains:

- schema version;
- session ID;
- round ID where applicable;
- sender ID;
- receiver ID or broadcast group;
- nonce;
- telemetry epoch;
- immutable typed payload.

Freshness is modeled through nonce and epoch checks. Cryptographic MACs are represented by an authenticity flag and policy result; version 1 does not implement real cryptographic primitives.

### 15.3 Prover round state

```python
class ProverRoundState(Enum):
    WAITING_FOR_CHALLENGE = "waiting_for_challenge"
    QND_IN_PROGRESS = "qnd_in_progress"
    MEMORY_LOADING = "memory_loading"
    COMMITTED_WITH_STATE = "committed_with_state"
    COMMITTED_WITHOUT_STATE = "committed_without_state"
    WAITING_FOR_BASIS = "waiting_for_basis"
    MEMORY_RETRIEVING = "memory_retrieving"
    MEASURING = "measuring"
    ANSWER_SENT = "answer_sent"
    NO_COMMITMENT = "no_commitment"
    ABORTED = "aborted"
    COMPLETE = "complete"
```

The transition table must be explicit and unit tested.

### 15.4 Verifier round state

```python
class VerifierRoundState(Enum):
    PLANNED = "planned"
    PREPARING = "preparing"
    CHALLENGE_SENT = "challenge_sent"
    BASIS_SENT = "basis_sent"
    COMMITMENT_RECEIVED = "commitment_received"
    LOCAL_MEASUREMENT_COMPLETE = "local_measurement_complete"
    ANSWER_RECEIVED = "answer_received"
    REPORT_SENT = "report_sent"
    ABORTED = "aborted"
    COMPLETE = "complete"
```

### 15.5 Controller round state

```python
class ControllerRoundState(Enum):
    CALIBRATING = "calibrating"
    PLANNING = "planning"
    PLAN_DISTRIBUTED = "plan_distributed"
    COLLECTING_REPORTS = "collecting_reports"
    DECIDING = "deciding"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABORTED = "aborted"
```

---

## 16. Timing and Security Metrics

Each round computes both physical and controller-observed values.

### 16.1 Commitment margin

\[
M_{commit} = t_{basis\ available} - t_{commit\ generated}.
\]

Record:

- physical margin;
- prover-local-clock margin;
- controller-inferred margin.

A negative physical margin means basis information was available before commitment generation.

### 16.2 Memory margin

\[
M_{memory}=T_{safe}-\tau_{memory}.
\]

`T_safe` is either the configured maximum hold time or the time at which predicted fidelity crosses the configured minimum.

### 16.3 Response margin

For verifier `i`:

\[
M_i^{response}=D_i-t_i^{arrival}.
\]

Record physical, local, and reported margins.

### 16.4 Causal margin

For two events `A` and `B`:

\[
M_{causal}=\|x_B-x_A\|-c|t_B-t_A|.
\]

Positive is spacelike, zero lightlike, negative causally connectable. The adversarial causal check uses vacuum light speed unless configured otherwise.

### 16.5 Spatial tolerance

For a round-trip timing-window change `Delta t`:

\[
\Delta r \approx v\Delta t/2.
\]

The geometry module computes accepted intervals in one dimension and accepted disk intersections on a configurable two-dimensional grid.

### 16.6 Session metrics

Required metrics:

- honest acceptance probability;
- attacker acceptance probability;
- false-accept rate outside authorized radius;
- false-reject rate at the claimed position;
- conditional QBER;
- commitment probability;
- valid-state commitment probability;
- average and percentile memory dwell time;
- timing-margin distributions;
- unsafe-plan approval rate;
- stale/replayed message rejection rate;
- attack detection rate;
- session completion probability;
- device utilization;
- channel transmissions, drops, and retries;
- event count and simulation execution time.

---

## 17. Attack Framework

### 17.1 Attack stages

```python
class AttackStage(Enum):
    INVENTORY = "inventory"
    PLAN = "plan"
    CLASSICAL_TRANSMISSION = "classical_transmission"
    QUANTUM_SEND = "quantum_send"
    QUANTUM_INTERCEPTION = "quantum_interception"
    REPORT = "report"
    RESULT = "result"
```

### 17.2 Attack interface

```python
class AttackModel(Protocol):
    attack_id: str

    def alter_inventory(self, snapshot: ResourceSnapshot, ctx: AttackContext) -> ResourceSnapshot: ...
    def alter_plan(self, plan: RoundPlan, ctx: AttackContext) -> RoundPlan: ...
    def alter_classical(self, tx: ClassicalTransmission, ctx: AttackContext) -> tuple[ClassicalTransmission, ...]: ...
    def decide_quantum_send(self, tx: QuantumTransmission, ctx: AttackContext) -> QuantumSendDecision: ...
    def alter_report(self, report: VerifierReport, ctx: AttackContext) -> VerifierReport: ...
    def alter_result(self, result: RoundResult, ctx: AttackContext) -> RoundResult: ...
```

Base implementations return the input unchanged. The pipeline applies attacks in configured order and logs every transformation.

### 17.3 Schedule-skew attack

Parameters:

```yaml
mode: early_basis | late_basis | asymmetric
x_shift_ps: 0
y_shift_ps: 0
challenge_shift_ps: 0
modify_controller_view: false
```

The attack may target the controller plan or basis messages in transit. It must support a case where physical timing changes but the controller retains the original expected schedule.

Expected effects:

- early basis can make the physical commitment margin negative;
- late basis increases memory dwell and quantum error;
- asymmetric skew can expose one verifier path while appearing acceptable in aggregate.

### 17.4 Telemetry-poisoning attack

Targets reported:

- memory `T1`, `T2`, or maximum hold;
- load/retrieval latency;
- detector efficiency;
- measurement latency;
- calibration timestamp.

Physical capabilities remain unchanged. The controller plans from attacked telemetry.

### 17.5 Timestamp-forgery attack

Parameters:

```yaml
node_id: v0
bias_ps: -1000000
fields:
  - commitment_arrival
  - answer_arrival
clamp_to_deadline: false
```

The attack changes only reported timestamps. Trace records must preserve physical and local values.

### 17.6 Selective-jamming attack

Supports:

- message-type filtering;
- source/destination filtering;
- active time window;
- deterministic drop;
- probabilistic drop;
- fixed or sampled added delay;
- quantum-send suppression.

Version 1 does not model RF interference; jamming is represented as link-level delay or loss.

### 17.7 Intercept–measure–resend attack

An explicit `SequenceInterceptorNode` is placed between `V0` and `P`.

Parameters:

```yaml
position_m: 2500
basis_strategy: random | z_only | x_only
processing_latency_ps: 500000
replacement_source_fidelity: 1.0
```

Behavior:

1. Receive challenge photon.
2. Choose attack basis.
3. Measure at completion of configured attacker measurement latency.
4. Prepare a replacement BB84 state with the measured bit and chosen basis.
5. Send replacement toward the prover after configured preparation latency.

The attack must not directly overwrite the honest result. It must manipulate the actual quantum state.

Under ideal, uniformly random BB84 bases, the validation test should observe approximately 25% QBER over a sufficiently large number of valid committed rounds, within a statistically justified tolerance.

---

## 18. Defense and Acceptance Policies

### 18.1 Baseline policy

The baseline approximates the trusted-control assumptions of the original architecture:

- accept reported capabilities within schema-valid ranges;
- use configured timing safety margin;
- trust verifier-reported timestamps;
- accept an authenticated-looking plan without cross-checking physical limits;
- abort on missing required verifier reports;
- enforce QBER and deadline thresholds.

### 18.2 Security-aware policy

The defended policy adds:

- nonce and telemetry-epoch freshness checks;
- maximum calibration age;
- hard bounds on reported device capabilities;
- consistency checks between hardware profile and telemetry;
- schedule-policy bounds on `delta`, basis skew, and operation windows;
- clock-uncertainty-aware timestamp validation;
- rejection when physical-model-predicted memory fidelity is below threshold;
- rejection when controller-inferred and reported timing differ beyond configured uncertainty;
- geometry-aware maximum authenticated radius;
- fail-closed behavior for critical missing messages.

### 18.3 Policy interfaces

```python
class TelemetryPolicy(Protocol):
    def validate(self, truth_profile: HardwareProfile, report: CapabilityReport, now_ps: SimTimePs) -> PolicyDecision: ...


class SchedulePolicy(Protocol):
    def validate(self, plan: RoundPlan, resources: ResourceSnapshot) -> PolicyDecision: ...


class AcceptancePolicy(Protocol):
    def decide(self, context: RoundDecisionContext) -> RoundDecision: ...
```

Policy decisions include machine-readable reason codes.

---

## 19. Configuration Specification

Use Pydantic v2 models and YAML input. Unknown fields are rejected by default.

### 19.1 Top-level configuration

```yaml
schema_version: "1.0"

simulation:
  seed: 12345
  stop_time: "10 ms"
  rounds: 1000
  quantum_formalism: density_matrix

execution:
  model: sequence_qpv
  parallel_processes: 1

geometry:
  dimension: 1
  propagation_speed_quantum_m_s: 2.0e8
  propagation_speed_classical_m_s: 2.0e8
  nodes:
    controller: {x_m: 0, y_m: 0}
    v0: {x_m: -5000, y_m: 0}
    prover: {x_m: 0, y_m: 0}
    v1: {x_m: 5000, y_m: 0}

hardware:
  v0:
    epr_source:
      generation_latency: "100 ns"
      success_probability: 1.0
      pair_fidelity: 0.99
      repetition_rate_hz: 1.0e6
    memory:
      load_latency: "200 ns"
      retrieve_latency: "200 ns"
      load_efficiency: 0.99
      retrieve_efficiency: 0.99
      t1: "100 us"
      t2: "20 us"
      maximum_hold: "50 us"
    measurement:
      basis_switch_latency: "50 ns"
      measurement_latency: "200 ns"
      measurement_fidelity: 0.99
      dead_time: "100 ns"

  prover:
    qnd:
      operation_latency: "300 ns"
      efficiency: 0.95
      dark_count_rate_hz: 10
      state_survival_probability: 0.99
      disturbance_probability: 0.01
      dead_time: "100 ns"
      gate_width: "2 us"
    memory:
      load_latency: "200 ns"
      retrieve_latency: "200 ns"
      load_efficiency: 0.98
      retrieve_efficiency: 0.98
      t1: "100 us"
      t2: "15 us"
      maximum_hold: "40 us"
    measurement:
      basis_switch_latency: "50 ns"
      measurement_latency: "250 ns"
      measurement_fidelity: 0.98
      dead_time: "100 ns"

links:
  quantum:
    - id: v0-prover
      source: v0
      destination: prover
      attenuation_db_per_m: 0.0002
      polarization_fidelity: 0.995
      frequency_hz: 8.0e7
  classical:
    - {id: controller-v0, source: controller, destination: v0}
    - {id: controller-v1, source: controller, destination: v1}
    - {id: controller-prover, source: controller, destination: prover}
    - {id: v0-prover, source: v0, destination: prover}
    - {id: prover-v0, source: prover, destination: v0}
    - {id: v1-prover, source: v1, destination: prover}
    - {id: prover-v1, source: prover, destination: v1}
    - {id: v0-controller, source: v0, destination: controller}
    - {id: v1-controller, source: v1, destination: controller}

protocol:
  basis_function: xor
  challenge_to_basis_delay: "5 us"
  commitment_window: "2 us"
  response_slack: "1 us"
  minimum_committed_rounds: 500
  maximum_qber: 0.10
  maximum_timing_violations: 0
  maximum_authenticated_radius_m: 100

controller:
  policy: baseline
  calibration_age_limit: "60 s"
  clock_uncertainty: "50 ns"

attacks: []

output:
  directory: "runs/qpv-ideal"
  trace_level: full
  write_round_csv: true
  write_event_ndjson: true
```

### 19.2 Validation rules

- Probabilities are in `[0,1]`.
- Durations are nonnegative.
- `T2 <= 2*T1` when both are present for the physical noise model.
- Link endpoints exist.
- Required directional classical links exist.
- Quantum link distance is either explicit or derivable from coordinates.
- Stop time exceeds the latest possible planned event plus cleanup margin.
- Minimum committed rounds do not exceed total rounds.
- Attack targets reference existing nodes, links, messages, or fields.
- Parallel process count is at least one.
- A full trace warning is emitted for large sweeps.

---

## 20. Tracing and Persistence

### 20.1 Event trace

`events.ndjson` uses one record per event:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "session_id": "session-0",
  "round_id": "round-000041",
  "event_id": "...",
  "physical_time_ps": 45120880,
  "phase": "DEVICE_COMPLETION",
  "node_id": "prover",
  "component_id": "prover.qnd",
  "event_type": "qnd_complete",
  "local_time_ps": 45121021,
  "reported_time_ps": null,
  "transmission_id": null,
  "quantum_object_id": "q-41-challenge",
  "attack_ids": ["schedule-skew-1"],
  "payload": {}
}
```

Trace payloads must not contain unserializable SeQUeNCe objects, NumPy arrays, or raw density matrices by default. Optional debug mode may store state summaries and fidelities, not full state matrices.

### 20.2 Round results

`rounds.csv` contains one row per round with stable columns, including:

- IDs and seed stream index;
- prover position;
- attack configuration identifier;
- commitment outcome;
- memory dwell;
- physical/local/reported timing margins;
- challenge survival;
- QND outcome;
- prover and verifier measurements;
- match flag;
- policy reason codes;
- accepted flag.

### 20.3 Summary

`summary.json` contains aggregates and confidence intervals. Proportions use Wilson intervals by default. Continuous metrics include mean, standard deviation, median, p90, p95, and p99 where sample size permits.

### 20.4 Atomic output

Write to a temporary run directory and atomically rename it on successful completion. Failed runs retain a `.failed` directory containing the manifest, exception, and trace up to failure.

---

## 21. CLI

Use Typer.

```text
qorchsim validate CONFIG
qorchsim run CONFIG [--output DIR] [--seed N]
qorchsim sweep SWEEP_CONFIG [--processes N]
qorchsim summarize RUN_DIR
qorchsim inspect RUN_DIR --round ROUND_ID
```

Requirements:

- `validate` performs schema and semantic validation without running SeQUeNCe.
- `run` creates one deterministic run.
- `sweep` expands a Cartesian or explicit parameter matrix and uses process-based parallelism.
- `summarize` regenerates aggregate results from persisted round data.
- `inspect` prints a chronological round trace and physical/local/reported timing differences.
- Commands return nonzero exit codes on validation or execution failures.

---

## 22. Experiment and Sweep Engine

### 22.1 Sweep format

```yaml
base_config: ../qpv_noisy.yaml
parameters:
  attacks[0].x_shift: ["-2 us", "-1 us", "0 us", "1 us", "2 us"]
  hardware.prover.memory.t2: ["5 us", "10 us", "20 us"]
replicates: 20
seed_strategy: deterministic_sequence
```

### 22.2 Expansion

Each expanded configuration receives:

- canonical parameter map;
- deterministic replicate seed;
- unique run ID;
- isolated output directory.

### 22.3 Parallelism

Use `concurrent.futures.ProcessPoolExecutor`. Never run multiple SeQUeNCe simulations in threads because of global quantum-manager formalism and potential shared global state.

### 22.4 Failure policy

A failed point does not cancel the sweep by default. The sweep summary records failed configurations and errors. `--fail-fast` is optional.

---

## 23. Testing Strategy

### 23.1 Unit tests

Pure domain tests cover:

- time conversion and rounding;
- event-priority encoding;
- state-transition tables;
- basis function;
- plan creation;
- nonce and epoch validation;
- clock conversion;
- attack transformations;
- policy decisions;
- geometry and causal margins;
- aggregation and confidence intervals;
- configuration normalization.

These tests must not initialize SeQUeNCe.

### 23.2 Component tests

SeQUeNCe-backed tests cover:

- EPR state fidelity;
- Z and X measurement correlations;
- quantum-channel propagation and loss;
- QND gate behavior and dark counts;
- memory load/retrieve timing;
- T1/T2 noise;
- measurement completion timing;
- local-clock observations;
- attackable classical channel drop, delay, mutation, and replay.

### 23.3 Protocol tests

- one ideal round completes and accepts;
- no challenge produces `c=0`;
- dark count produces commitment without state;
- basis arriving before commitment yields negative physical margin;
- missing one basis input prevents measurement and causes timeout;
- stale round plan is rejected under defended policy;
- duplicate answer is detected;
- physical and reported timestamps remain distinct.

### 23.4 Attack validation tests

#### Schedule skew

- early skew changes physical commitment margin by the configured amount;
- late skew increases memory dwell by the configured amount, subject to device latency;
- security-aware policy rejects configured unsafe bounds.

#### Telemetry poisoning

- physical memory uses actual `T2`;
- controller plan uses attacked reported `T2` under baseline policy;
- defended policy rejects out-of-profile telemetry.

#### Timestamp forgery

- physical and local times remain unchanged;
- only the report changes;
- defended policy detects bias exceeding uncertainty.

#### Selective jamming

- targeted messages are dropped or delayed exactly according to seeded decisions;
- untargeted messages are unaffected.

#### Intercept–measure–resend

- attacker manipulates actual quantum state;
- ideal long-run QBER is statistically consistent with 25% for random-basis interception.

### 23.5 Analytical validation tests

1. **Propagation:** `arrival - send = round(distance/light_speed)` according to the selected channel model.
2. **Delay-to-distance:** a round-trip timing-window increase `Delta t` changes the ideal boundary by approximately `v*Delta t/2`.
3. **Memory:** simulated coherence matches the configured analytical channel within numerical tolerance.
4. **Detector:** detection count matches binomial expectation and dark counts match Poisson expectation within statistical tolerance.
5. **Ideal EPR:** same-basis measurements match with probability one in the no-noise model.

### 23.6 Regression tests

Maintain small golden outputs for:

- 10 ideal rounds;
- 10 schedule-skew rounds;
- 10 intercept–resend rounds.

Golden traces exclude wall-clock metadata. Any intentional schema or behavior change requires an explicit fixture update and changelog entry.

### 23.7 Property-based tests

Use Hypothesis for:

- valid state-machine transition sequences;
- attack pipeline identity behavior;
- clock monotonicity under bounded drift and no negative jitter;
- immutable message round-trip serialization;
- geometry symmetry;
- Kraus-channel trace preservation.

### 23.8 Coverage

Required coverage:

- domain/core/policies/attacks: at least 95%;
- overall package: at least 85%;
- all critical state transitions explicitly covered.

---

## 24. Code Quality and Tooling

### 24.1 Dependencies

Runtime:

```toml
sequence = "==1.0.0"
pydantic = ">=2.11,<3"
pyyaml = ">=6.0,<7"
typer = ">=0.16,<1"
numpy = ">=2.3,<3"
pandas = ">=2.3,<3"
```

Development:

```toml
pytest = ">=9,<10"
pytest-cov = ">=7,<8"
hypothesis = ">=6,<7"
ruff = ">=0.15,<1"
mypy = ">=1.18,<2"
```

Do not add a dependency unless it materially reduces complexity or improves correctness.

### 24.2 Formatting and linting

- Ruff format.
- Ruff lint with import sorting, bugbear, comprehensions, pyupgrade, and security-relevant rules.
- Maximum line length: 100.
- No wildcard imports.
- No mutable default arguments.
- No bare `except`.

### 24.3 Typing

- Domain and application code must pass strict mypy.
- SeQUeNCe adapters may use narrowly scoped ignores with comments because upstream typing is incomplete.
- Public functions and methods require type annotations.
- Domain dataclasses should be frozen where practical.

### 24.4 Documentation

- Every public class and protocol has a docstring.
- Complex timing behavior includes an event-order comment.
- Each attack documents what physical, observed, or reported state it changes.
- Each configuration field has a description and unit.

### 24.5 Logging

Use Python structured logging with run, session, round, node, and component context. Logging is separate from the canonical event trace and may be disabled for large experiments.

---

## 25. Error Model

Typed errors include:

```text
ConfigurationError
UnsupportedSequenceVersionError
PastEventError
DuplicateEventError
InvalidStateTransitionError
InvalidDeviceStateError
ResourceUnavailableError
ProtocolViolationError
FreshnessViolationError
UnknownRoundError
QuantumStateValidationError
TraceSerializationError
```

Expected operational outcomes such as photon loss, detector miss, timeout, policy rejection, or attack detection are not exceptions.

---

## 26. Performance Requirements

Version 1 performance targets on a typical modern workstation:

- 1,000 ideal QPV rounds complete in less than 60 seconds with summary tracing.
- 10,000 abstract protocol events execute without unbounded memory growth.
- Full event tracing may be slower but must stream to disk rather than retain the entire trace in memory.
- Event-pump registry size must remain proportional to pending events and release entries after dispatch.
- Per-round state must be released after result persistence unless debug retention is enabled.
- Sweep parallelism must scale through processes without sharing SeQUeNCe objects.

Performance tests are advisory in local development and enforced with generous thresholds in a dedicated benchmark job, not normal unit tests.

---

## 27. Security and Scientific Integrity Requirements

- The output must state which attack strategies were simulated.
- The software must not label the system “secure” based only on simulation.
- Physical truth, observed telemetry, and reported telemetry must never be collapsed into one field.
- Attack code must not directly set final acceptance unless the attack explicitly targets a compromised controller result; such behavior must be visible in the trace.
- Intercept attacks must manipulate quantum state through `QuantumOperations`.
- All model assumptions and parameter sources must be recorded in the manifest or accompanying experiment documentation.
- Unsupported SeQUeNCe versions must be rejected by default.
- Numerical state validation must run after custom Kraus operations in test and debug modes.

---

## 28. Implementation Plan

### Phase 0 — Repository bootstrap

Deliverables:

- `pyproject.toml` with pinned dependencies and CLI entry point;
- package skeleton;
- Ruff, mypy, pytest, coverage configuration;
- basic CI workflow;
- README with installation and development commands;
- version guard for SeQUeNCe.

Acceptance:

- `uv sync` succeeds;
- `ruff check`, `ruff format --check`, `mypy`, and `pytest` run successfully;
- `qorchsim --help` works.

### Phase 1 — Domain core and configuration

Deliverables:

- time and ID types;
- event phases and priority encoding;
- clock, scheduler, event bus, trace interfaces;
- random-stream registry;
- Pydantic configuration models;
- YAML loader and normalized configuration;
- CloudSim-compatible workload/resource/allocation interfaces;
- static QPV scheduler.

Acceptance:

- configuration examples validate;
- invalid units, links, and probabilities fail with precise errors;
- domain unit tests run without SeQUeNCe initialization.

### Phase 2 — SeQUeNCe kernel adapter

Deliverables:

- timeline creation;
- event pump and event scheduler;
- deterministic encoded priorities;
- node and protocol bridges;
- trace integration;
- version guard;
- process-safe runner boundary.

Acceptance:

- scheduled domain events execute in deterministic `(time, phase, sequence)` order;
- past events fail immediately;
- same-seed traces are identical;
- event-pump registry is empty after a completed minimal run.

### Phase 3 — Quantum operations and devices

Deliverables:

- EPR creation;
- BB84 preparation and measurement;
- Kraus-channel engine;
- EPR source;
- QND detector;
- timed memory;
- timed measurement device;
- local clock;
- device telemetry.

Acceptance:

- ideal EPR correlations pass;
- X-basis measurements are correct under quantum-manager use;
- memory noise matches analytical expectations;
- QND statistical tests pass;
- all device state transitions are tested.

### Phase 4 — Network and QPV protocol

Deliverables:

- geometry and link builder;
- attackable classical channels;
- quantum channel setup;
- controller, verifier, and prover state machines;
- multi-round session service;
- baseline acceptance policy;
- event and round persistence.

Acceptance:

- ideal noiseless session accepts;
- lossy sessions produce commitments consistent with detector/channel behavior;
- all protocol timeouts and freshness checks behave deterministically;
- round traces show the complete event sequence.

### Phase 5 — Attacks and defenses

Deliverables:

- attack pipeline;
- five required attacks;
- security-aware policies;
- attack-specific configuration;
- attack detection and reason codes.

Acceptance:

- each attack has unit, integration, and scientific validation tests;
- physical, local, and reported timelines remain distinguishable;
- intercept–resend produces expected QBER;
- defended policy rejects unsafe plans and telemetry in configured cases.

### Phase 6 — Metrics, CLI, and sweeps

Deliverables:

- metrics aggregation;
- confidence intervals;
- CLI commands;
- sweep expansion;
- process-based parallel execution;
- run summaries and inspection output.

Acceptance:

- all example configurations run from CLI;
- sweep results are reproducible;
- failed sweep points are recorded without corrupting other outputs;
- output schemas are documented.

### Phase 7 — Validation and hardening

Deliverables:

- golden regression fixtures;
- analytical validation suite;
- performance tests;
- documentation of model assumptions;
- example notebooks or scripts for publication figures;
- final coverage report.

Acceptance:

- all Definition of Done criteria below pass;
- no placeholder implementations or `TODO` markers remain in version-1 paths;
- package installs cleanly in a new environment.

---

## 29. Definition of Done

The implementation is complete only when all of the following are true:

1. The project installs with Python 3.12 and SeQUeNCe 1.0.0.
2. All tests pass with required coverage.
3. An ideal 1,000-round QPV session completes and produces deterministic output.
4. Quantum-channel propagation matches configured geometry.
5. EPR same-basis measurement correlation is correct in the ideal model.
6. QND loss, efficiency, dark-count, and disturbance behaviors are tested.
7. Memory loading, storage noise, retrieval, and expiration are explicitly timed.
8. Physical, local, and reported timestamps are present in traces and results.
9. The five required attacks are fully implemented and configurable.
10. Intercept–measure–resend manipulates the actual quantum state and yields the expected ideal QBER range.
11. Schedule skew changes physical timing and quantum memory dwell as expected.
12. Telemetry poisoning changes controller-visible capabilities but not physical device behavior.
13. Security-aware policies reject unsafe configurations in defined test cases.
14. CLI validation, run, sweep, summarize, and inspect commands work.
15. Run outputs include manifest, NDJSON trace, round CSV, and summary JSON.
16. The domain, attack, policy, workload, resource, scheduler, and metric packages contain no SeQUeNCe imports.
17. The QPV workload runs through `SchedulerPolicy` and `ExecutionModel` interfaces rather than directly invoking the scenario builder.
18. The code contains no incomplete stubs in the version-1 execution path.
19. README documentation includes installation, architecture, configuration, attack examples, and reproduction instructions.
20. The system explicitly describes results as evaluations of implemented attacks rather than a general security proof.

---

## 30. Future CloudSim-Style Extension Path

The following features are not built in version 1, but the architecture must make them additive:

### 30.1 Workload arrival and queues

Add a workload broker that emits arrivals over time and maintains pending, admitted, running, completed, failed, and preempted states.

### 30.2 Resource reservations

Extend resources with time-indexed availability calendars and atomic multi-resource gang reservations.

### 30.3 Scheduling policies

Add:

- first-fit;
- earliest-finish;
- fidelity-aware;
- security-aware;
- topology-aware;
- fair-share;
- priority and preemptive;
- deadline-aware;
- reinforcement-learning policies behind the same interface.

### 30.4 Multiple execution fidelities

Add:

- analytical execution model;
- stochastic execution model;
- detailed SeQUeNCe execution model.

The scheduler and attack framework remain unchanged.

### 30.5 Additional workloads

Add QKD, entanglement distribution, distributed quantum computation, sensing, and anonymous transmission as new `Workload` and `ExecutionModel` implementations.

### 30.6 Broader network attacks

Add resource exhaustion, reservation hoarding, link-state poisoning, compromised schedulers, congestion models, and multi-tenant interference. If classical packet networking becomes central, add an alternate network backend without changing domain workload or attack definitions.

### 30.7 Multi-verifier QPV

Generalize verifier collections and add Byzantine quorum geometry, robust verifier selection, and geometry-aware degraded operation.

---

## 31. Key Architectural Decisions

### ADR-001: Use SeQUeNCe as backend, not domain model

**Decision:** Only the adapter package imports SeQUeNCe.  
**Reason:** Retains physical timing and quantum-state support while preserving future execution backends.

### ADR-002: Use density-matrix formalism

**Decision:** Version 1 uses SeQUeNCe density-matrix quantum manager.  
**Reason:** Required for nonunitary memory and source noise and small enough for the two-qubit honest protocol and simple intercept attacks.

### ADR-003: Use one SeQUeNCe timeline per process

**Decision:** No threaded concurrent simulations.  
**Reason:** SeQUeNCe quantum-manager formalism is global and process isolation improves determinism.

### ADR-004: Encode deterministic event order into priority

**Decision:** Priority combines event phase and monotonic sequence.  
**Reason:** SeQUeNCe events otherwise have no stable tie breaker for equal time and priority.

### ADR-005: Build custom QPV devices

**Decision:** Implement QND, timed memory, and timed measurement components.  
**Reason:** Stock devices do not directly provide the required commitment-QPV semantics.

### ADR-006: Model interceptor as a node

**Decision:** Intercept–measure–resend uses explicit topology and quantum operations.  
**Reason:** Prevents attacks from bypassing quantum-state evolution and timing.

### ADR-007: Introduce minimal CloudSim abstractions now

**Decision:** QPV executes as a workload through scheduler and execution-model interfaces.  
**Reason:** Enables later cloud scheduling research without imposing Kubernetes or full resource-management complexity on version 1.

### ADR-008: Persist streamed event traces

**Decision:** NDJSON is the canonical detailed trace.  
**Reason:** It is appendable, inspectable, resilient to partial failure, and simulator-independent.

---

## 32. Principal Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| SeQUeNCe API drift | Adapter breakage | Pin 1.0.0; startup guard; isolate adapter |
| Incorrect composite-state noise | Invalid quantum results | Kraus unit tests; state validation; analytical comparisons |
| Same-time event ambiguity | Security result depends on heap behavior | Encoded phase and sequence priority |
| Hidden nondeterminism | Irreproducible paper results | Named RNG streams; process isolation; golden traces |
| Overly broad scope | Incomplete simulator | Enforce explicit non-goals and phased Definition of Done |
| QND model overclaim | Misleading physical conclusions | Call it an abstract probabilistic device; parameter sensitivity |
| Trace volume | Disk and runtime overhead | Summary trace level; streaming writes; optional sampling |
| Controller policy coupled to QPV | Poor CloudSim reuse | Generic workload/resource/scheduler interfaces |
| Attack directly changes decision | Unrealistic security evaluation | Stage-specific attack APIs and trace audits |
| Configuration errors create impossible physics | Invalid results | Strict Pydantic validation and runtime invariants |

---

## 33. Expected Initial Experiments

The completed simulator must support these publication-oriented experiments without code changes:

1. Honest acceptance versus memory `T2` and challenge-to-basis delay.
2. Honest and attacker acceptance versus schedule skew.
3. Physical versus controller-inferred commitment margin under compromised scheduling.
4. Unsafe-plan approval rate under memory-capability falsification.
5. False-reject rate under late basis delivery and memory decoherence.
6. Reported versus physical deadline compliance under timestamp forgery.
7. Availability and security under selective jamming.
8. QBER and acceptance under intercept–measure–resend.
9. One-dimensional or two-dimensional acceptance heatmaps over prover position.
10. Baseline versus security-aware policy comparisons.

---

## 34. Build Instruction Contract

When implementation begins, the code must follow this specification exactly unless a concrete incompatibility with SeQUeNCe 1.0.0 is discovered. In that case:

1. preserve the architectural boundary and scientific behavior;
2. document the incompatibility in `IMPLEMENTATION_NOTES.md`;
3. make the smallest necessary change;
4. add a regression test for the adapted behavior;
5. do not silently omit a required feature.

The implementation must deliver functioning code, tests, configurations, CLI commands, and documentation. Placeholder methods, unimplemented required attacks, and test-only mock behavior in production execution paths are not acceptable.
