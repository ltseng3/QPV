# QOrchSim Build Report

**Build:** 0.1.0  
**Completed:** 2026-08-02  
**Local runtime:** Python 3.13.5

## Delivered

- installable Python package and wheel;
- deterministic picosecond event kernel and SeQUeNCe timeline adapter;
- density-matrix EPR, BB84, memory noise, and quantum attack operations;
- timed source, QND detector, memory, measurement, and clocks;
- complete multi-round two-verifier commitment-QPV protocol;
- five configurable attacks;
- baseline and security-aware policies;
- CloudSim-style workload/resource/scheduler/allocation/execution interfaces;
- CLI validation, run, sweep, summarize, and inspect commands;
- atomic manifest, NDJSON, CSV, and JSON outputs;
- example configurations, attack scenarios, sweeps, scripts, architecture docs, and five tutorials;
- unit, component, protocol, attack, integration, analytical, regression, and performance tests.

## Automated tests

Final local command:

```bash
python -m pytest --cov=qorchsim --cov-report=term --cov-fail-under=85
```

Result:

```text
57 passed, 2 skipped
90.47% total coverage
```

Skipped tests:

- SeQUeNCe integration, because `sequence==1.0.0` was unavailable from the build
  environment's package mirror;
- Hypothesis properties, because `hypothesis` was unavailable from that mirror.

The suite includes deterministic golden hashes for ideal, schedule-skew, and
intercept-resend ten-round scenarios.

## 1,000-round deterministic validation

Two independent portable-backend executions with the same normalized configuration and
seed produced byte-identical canonical artifacts.

```text
rounds:                 1000
committed rounds:       1000
accepted rounds:        988
QBER:                    0.012
critical timing errors: 0
session accepted:       true
event records:          29000
CSV lines:              1001
```

Canonical SHA-256 hashes:

```text
events.ndjson  01b9b6568c85a4cb6ce050b34644464bb86476858815e33c9a022c19aaef345c
rounds.csv     e287d521f92a843101a1a9b280abd8f10f4c1bee1abe5eabe30e4673853f6ca6
summary.json   405219e6cb8d1248c04383b62af62b308230522a956147829132bac98409862b
```

## Scenario validation

The ideal, noisy, and all five attack configurations completed successfully after being
switched to the portable validation backend. A four-point process-parallel portable
sweep completed with zero failed points.

## Packaging

The wheel built successfully with no dependency resolution during the build step:

```text
dist/qorchsim-0.1.0-py3-none-any.whl
SHA-256: 1d78022af70282e09d5f572d6289c83c5f6a810ad4ab4f15e4a1a11cae7b510f
```

The final wheel should be installed in an environment that can resolve the pinned
runtime dependencies, including SeQUeNCe 1.0.0 for the detailed backend.

## Import-boundary audit

The only direct `sequence.*` imports are in:

```text
qorchsim.adapters.sequence.scheduler
qorchsim.adapters.sequence.event_pump
```

The density-manager adapter receives the manager instance from the SeQUeNCe timeline
and does not leak it into domain APIs.

## Scientific caution

Outputs quantify the behavior of the implemented physical models, controller policies,
and attack strategies. They do not constitute a proof of security against arbitrary or
unbounded quantum adversaries.
