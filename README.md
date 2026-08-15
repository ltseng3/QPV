# QOrchSim

QOrchSim is a modular discrete-event simulator for security evaluation of
SDN-orchestrated commitment-based quantum position verification (QPV). It is designed
to evolve into a CloudSim-style simulator for quantum-network resource scheduling and
coordination.

## Implemented features

- deterministic integer-picosecond virtual time;
- SeQUeNCe 1.0.0 timeline adapter and portable deterministic test backend;
- exact density-matrix EPR and BB84 operations;
- timed EPR source, QND presence detector, quantum memory, and measurement device;
- T1/T2 memory noise using subsystem Kraus channels;
- physical, local-clock, and reported timestamps;
- complete multi-round two-verifier commitment-QPV session;
- schedule skew, telemetry poisoning, timestamp forgery, selective jamming, and
  intercept-measure-resend attacks;
- baseline and security-aware acceptance policies;
- immutable workloads, resources, allocations, scheduler and execution interfaces;
- YAML configuration, CLI, sweeps, streaming NDJSON traces, CSV round records, and
  JSON summaries;
- unit, component, protocol, attack, analytical-validation, and regression tests.

## Installation

Python 3.12–3.14 is supported.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

The production backend pins SeQUeNCe exactly:

```bash
python -m pip install sequence==1.0.0
```

## Commands

```bash
qorchsim validate configs/qpv_ideal.yaml
qorchsim run configs/qpv_ideal.yaml --output runs/ideal
qorchsim sweep configs/sweeps/skew_vs_memory.yaml --output runs/skew-sweep -p 4
qorchsim summarize runs/ideal
qorchsim inspect runs/ideal --round round-000000
```

## Development without SeQUeNCe

The portable backend exists for fast domain and protocol tests:

```python
config = config.model_copy(
    update={"execution": config.execution.model_copy(update={"model": "portable_qpv"})}
)
```

It uses the same event phases, devices, attacks, policies, quantum operations, traces,
and outputs. Publication runs should use `sequence_qpv` after installing SeQUeNCe
1.0.0.

## Output interpretation

Simulation results characterize the implemented attack strategies and model
assumptions. They are not a general security proof of quantum position verification.
Physical truth, local observations, and reported telemetry are kept separate in all
security-relevant records.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration reference](docs/configuration.md)
- [Testing and validation](docs/testing.md)
- [Quick start](docs/tutorials/01_quickstart.md)
- [Attack tutorial](docs/tutorials/02_attacks.md)
- [Extension tutorial](docs/tutorials/03_extending.md)
- [CloudSim-style extension tutorial](docs/tutorials/04_cloudsim_extension.md)
- [Reproduction tutorial](docs/tutorials/05_reproduction.md)
- [Technical specification](TECHNICAL_SPEC.md)
- [Implementation notes](IMPLEMENTATION_NOTES.md)
- [Build report](BUILD_REPORT.md)

## Testing

```bash
pytest
pytest --cov=qorchsim --cov-report=term-missing
```

Tests marked `sequence` require SeQUeNCe 1.0.0. All other tests use the portable
backend and do not import SeQUeNCe. See [Testing and validation](docs/testing.md) for
the integration lane, determinism checks, property tests, and static-analysis commands.

## Examples

```bash
python examples/run_portable_smoke.py
python examples/compare_policies.py
python examples/custom_attack.py
python examples/custom_scheduler.py
```

The examples are intentionally small and executable. The tutorials explain how their
interfaces connect to complete QPV experiments.
