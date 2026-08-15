# Tutorial 1: Quick Start

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

SeQUeNCe publication runs require exactly version 1.0.0:

```bash
python -m pip install sequence==1.0.0
```

## Validate

```bash
qorchsim validate configs/qpv_ideal.yaml
```

Validation rejects unknown fields, invalid probability ranges, nonphysical `T1/T2`
combinations, missing directional links, and an insufficient simulation horizon.

## Run

```bash
qorchsim run configs/qpv_ideal.yaml --output runs/ideal
```

A successful run contains:

```text
manifest.json
summary.json
rounds.csv
events.ndjson
```

Inspect one round:

```bash
qorchsim inspect runs/ideal --round round-000000
```

## Python API

```python
from qorchsim.config.loader import load_config
from qorchsim.experiments.runner import run_experiment

config = load_config("configs/qpv_ideal.yaml")
artifacts = run_experiment(config, output_directory="runs/from-python")
print(artifacts.summary["security"]["qber"])
```
