# Tutorial 5: Reproducing and Inspecting Results

## Run a baseline and an attack

```bash
qorchsim run configs/qpv_smoke.yaml -o runs/tutorial-baseline
qorchsim run configs/attacks/schedule_skew.yaml -o runs/tutorial-skew
```

## Inspect one round

```bash
qorchsim inspect runs/tutorial-skew --round round-000000
```

The command prints the stable round row followed by chronological events. Compare:

- physical commitment margin;
- controller-inferred commitment margin;
- memory dwell time;
- physical, local, and reported arrival timestamps;
- attack identifiers attached to transmissions and reports.

## Summarize persisted data

```bash
qorchsim summarize runs/tutorial-skew
```

This recomputes a compact summary from `rounds.csv`, which is useful when analysis code
changes without rerunning the physical simulation.

## Run a sweep

```bash
qorchsim sweep configs/sweeps/skew_vs_memory.yaml \
  --output runs/tutorial-sweep \
  --processes 4
```

Each expanded point receives a deterministic seed, isolated output directory, and
status entry in the sweep result. One failed point does not corrupt successful points.

## Python analysis example

```python
from pathlib import Path
import json
import pandas as pd

run = Path("runs/tutorial-skew")
rounds = pd.read_csv(run / "rounds.csv")
summary = json.loads((run / "summary.json").read_text())

print("accepted fraction:", rounds["accepted"].mean())
print("median physical margin (ps):", rounds["physical_commitment_margin_ps"].median())
print("QBER:", summary["security"]["qber"])
```

## Scientific interpretation

The simulator evaluates the attacks, hardware models, and controller policies encoded
in the configuration. It does not prove security against arbitrary quantum adversaries.
Always report the attack strategy, resource limits, noise model, and timing assumptions
alongside numerical results.
