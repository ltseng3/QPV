# Testing and Validation Guide

QOrchSim separates fast portable tests from the external SeQUeNCe integration lane.
The portable lane exercises domain state machines, exact density-matrix operations,
devices, attacks, scheduling contracts, persistence, and CLI behavior. The integration
lane verifies that the adapter can use SeQUeNCe 1.0.0's timeline and density-matrix
manager.

## Run the complete suite

```bash
python -m pytest
```

## Coverage

```bash
python -m pytest \
  --cov=qorchsim \
  --cov-report=term-missing \
  --cov-fail-under=85
```

The project configuration enforces 85% overall coverage. Critical state-machine and
security transitions have direct tests even where aggregate coverage is higher.

## SeQUeNCe integration lane

Install the pinned runtime and run the marked test:

```bash
python -m pip install sequence==1.0.0
python -m pytest -m sequence
```

The test is skipped rather than emulated when the package is not available. This makes
it clear whether a result came from the real adapter or the portable validation lane.

## Property-based tests

```bash
python -m pip install hypothesis
python -m pytest tests/unit/test_property_contracts.py
```

Properties include trace-preserving quantum channels, clock behavior, and immutable
attack transformations.

## Test taxonomy

- `tests/unit`: pure domain, configuration, quantum algebra, and adapter-contract tests.
- `tests/component`: timed source, detector, memory, and measurement behavior.
- `tests/protocol`: complete round/session state-machine behavior.
- `tests/attacks`: stage-specific attack and policy validation.
- `tests/integration`: CLI, output persistence, sweep, version guard, and SeQUeNCe lane.
- `tests/validation`: analytical propagation, delay-to-distance, and quantum checks.
- `tests/regression`: deterministic golden artifact hashes.
- `tests/performance`: advisory smoke performance.

## Determinism test

Run the same configuration twice with the same seed and compare canonical artifacts:

```bash
qorchsim run configs/qpv_smoke.yaml -o /tmp/qorchsim-a
qorchsim run configs/qpv_smoke.yaml -o /tmp/qorchsim-b
sha256sum /tmp/qorchsim-a/{events.ndjson,rounds.csv,summary.json}
sha256sum /tmp/qorchsim-b/{events.ndjson,rounds.csv,summary.json}
```

The hashes should match. `manifest.json` may include environment metadata, so the three
canonical result files are the deterministic comparison target.

## Static checks

```bash
ruff format --check src tests examples
ruff check src tests examples
mypy src/qorchsim
python -m compileall -q src tests examples
```

The SeQUeNCe adapter is excluded from strict mypy because upstream framework typing is
incomplete; its public boundary is covered by contract and integration tests.

## Adding a test for an attack

An attack test should assert all three data planes explicitly:

1. **Physical truth** changed only when the attack is physical.
2. **Local observation** changed only when the device or clock is affected.
3. **Reported value** changed when telemetry is forged.

For example, timestamp forgery must leave physical and local timestamps unchanged while
changing the report. Schedule skew must change physical transmission timing and cannot
be tested by editing only a controller decision.
