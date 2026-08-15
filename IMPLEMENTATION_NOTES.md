# Implementation Notes

**Implementation version:** 0.1.0  
**Specification:** `TECHNICAL_SPEC.md` version 1.0  
**Build date:** 2026-08-02

## Implemented architecture

The implementation preserves the specification's strict adapter boundary:

- domain, QPV, attack, policy, resource, scheduling, metrics, and persistence code are
  plain Python;
- only `qorchsim.adapters.sequence` imports SeQUeNCe;
- QPV executes as a `Workload` through `SchedulerPolicy` and `ExecutionModel`;
- physical, local-clock, and reported timestamps are distinct;
- quantum state changes are performed through a `QuantumOperations` contract;
- the portable and SeQUeNCe adapters implement the same scheduling and quantum contracts.

## SeQUeNCe integration detail

The SeQUeNCe adapter uses:

- the framework `Timeline`, `Event`, and `Process` objects for virtual-time dispatch;
- the timeline's density-matrix quantum manager as the authoritative state store;
- public manager operations for state creation, replacement, circuit execution, and
  measurement.

The QPV-specific source, QND detector, memory, measurement, attackable transmissions,
and protocol state machines remain QOrchSim domain components. They schedule through
the SeQUeNCe timeline rather than subclassing every SeQUeNCe photonic component. This
is the smallest adaptation that preserves timing and density-matrix semantics while
keeping the protocol and future CloudSim layer backend-independent.

Direct SeQUeNCe node/channel/device binding values are included as adapter seams for
future experiments that need framework topology objects. They are not required by the
version-1 execution path.

## Portable validation backend

`portable_qpv` is a deterministic execution backend, not a probabilistic result mock.
It executes the complete protocol, timed devices, density matrices, Kraus noise,
attacks, policies, traces, and persistence using QOrchSim's scheduler implementation.
It exists to:

- run fast unit and protocol tests;
- validate scientific behavior when SeQUeNCe is unavailable;
- provide a reference contract for the SeQUeNCe adapter;
- support future analytical and stochastic execution models.

Publication-oriented runs should use `sequence_qpv` and repeat the integration suite in
an environment with SeQUeNCe 1.0.0 installed.

## Environment limitations during this build

The build environment's package mirror did not provide these packages:

- `sequence==1.0.0`;
- `hypothesis`;
- `ruff`;
- `mypy`.

Consequences:

1. The real SeQUeNCe integration test is included but was skipped locally. The adapter's
   density-manager behavior is covered by a public-contract test double.
2. The Hypothesis property test is included but was skipped locally.
3. Ruff and mypy configuration is included, but those tools could not be executed in
   this environment.

No result is represented as a completed SeQUeNCe integration run when it came from the
portable backend.

## Round-isolation correction discovered during hardening

A noisy multi-round example exposed a timing edge case: when QND detection failed, the
verifier's retained qubit could remain in its one-slot memory until forced reports and
the final timeout completed, while the next round was scheduled earlier. The round
period estimator now includes both controller-report propagation windows and timeout
slack. A regression test verifies that repeated no-commitment rounds release resources
before the next allocation.

## Model limitations

- The QND detector is an abstract probabilistic presence detector, not an optical-mode
  simulation.
- Classical jamming is modeled as deterministic/stochastic delay or drop, not RF
  interference.
- The simulator evaluates configured attacks and bounded strategies; it is not a
  general QPV security proof.
- Version 1 has a static gang scheduler and no workload queue, contention calendar, or
  preemption. The interfaces required for those CloudSim-style extensions are present.
- The detailed model is two-verifier QPV. Multi-verifier Byzantine geometry remains
  future work.

## Re-running the unverified lanes

```bash
python -m pip install sequence==1.0.0 hypothesis ruff mypy
python -m pytest -m sequence
python -m pytest tests/unit/test_property_contracts.py
ruff format --check src tests examples
ruff check src tests examples
mypy src/qorchsim
```
