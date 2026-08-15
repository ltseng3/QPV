# Spatial assurance analysis

The `qorchsim.assurance` package implements the analytical timing-assurance model used
for the MILCOM probabilistic-spatial-assurance study. It is intentionally separate from
the detailed two-verifier commitment-QPV discrete-event runtime.

## Scope

For verifier `i` and candidate prover position `p`, the package evaluates

```text
m_i(p) = T_i - tau_i - 2 ||p - v_i|| / c
a_i(p) = F_i(m_i(p))
A(p)   = product_i a_i(p)
```

where `F_i` is the calibrated residual timing-error CDF. `A(p)` is the probability that
an honest prover at `p` passes all configured timing checks under independent verifier
timing errors. It is **not** a posterior probability over prover position and it is not
a cryptographic QPV soundness probability.

The implementation currently provides:

- zero-mean or biased Gaussian timing errors;
- empirical timing distributions represented by calibration samples;
- arbitrary two-dimensional verifier geometry;
- local and joint spatial assurance;
- deterministic timing-feasible masks;
- Cartesian-grid assurance fields;
- fixed-assurance area and worst-case spatial extent metrics;
- exact repeated-round binomial timing assurance;
- the Hoeffding sufficient round-count bound from the paper.

The theoretical correlated-error extension in the paper is deliberately not part of
the initial publication implementation. Keeping the independent model explicit makes
the evaluation easy to audit and keeps the software aligned with the equations used in
the numerical section.

## Paper study

Three configurations are provided under `configs/paper/`:

- `assurance_healthy.yaml`: four verifiers, each with 1 ns Gaussian residual jitter;
- `assurance_degraded.yaml`: identical geometry/deadlines, but the east verifier has
  5 ns residual jitter;
- `assurance_degraded_removed.yaml`: the degraded east verifier is excluded.

All values are synthetic, controlled parameters chosen to expose the model behavior.
They must not be described as hardware measurements.

Generate the numerical artifacts with:

```bash
python scripts/paper/generate_assurance_data.py   --output runs/paper-assurance
```

Then render the paper figures from those immutable artifacts:

```bash
python scripts/paper/plot_assurance_study.py   --data runs/paper-assurance   --output runs/paper-assurance/figures
```

The first command creates:

```text
healthy.npz
degraded.npz
removed.npz
degradation_sweep.csv
repetition.npz
metrics.json
manifest.json
```

The second command creates both PDF and 300-DPI PNG copies of:

```text
fig_assurance_regions
fig_degradation
fig_repetition
```

Keeping data generation separate from rendering prevents cosmetic plot edits from
silently changing the scientific results.

## Interpretation

`fig_assurance_regions` compares deterministic timing geometry with 0.90, 0.99, and
0.999 assurance contours. The degraded scenario demonstrates a key operational point:
the deterministic feasible region is unchanged when only timing variance increases,
while high-assurance regions may shrink or disappear.

`fig_degradation` sweeps only the east-verifier timing standard deviation. The useful
controller quantities are `A(p*)`, the assurance at the intended position, and
`max_p A(p)`, which establishes whether a requested assurance level is achievable at
all.

`fig_repetition` applies a 90% successful-round session threshold and shows how larger
round counts sharpen the timing decision around the same underlying single-round
assurance contour. This is timing-decision concentration, not cryptographic security
amplification.

## Validation

Run the focused tests with:

```bash
pytest tests/unit/test_assurance.py tests/integration/test_assurance_paper.py
```

Before publication, also run the project's normal quality gates:

```bash
pytest
ruff format --check src tests examples scripts
ruff check src tests examples scripts
mypy src/qorchsim
```

For any paper numbers, archive `manifest.json`, `metrics.json`,
`degradation_sweep.csv`, and the exact Git commit hash used to produce them.
