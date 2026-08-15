#!/usr/bin/env python3
"""Generate machine-readable spatial-assurance artifacts for the MILCOM paper."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from qorchsim.assurance.field import assurance_grid
from qorchsim.assurance.io import load_assurance_deployment
from qorchsim.assurance.regions import deterministic_grid, region_metrics
from qorchsim.assurance.repetition import session_assurance
from qorchsim.network.geometry import Position


SCENARIOS = {
    "healthy": "configs/paper/assurance_healthy.yaml",
    "degraded": "configs/paper/assurance_degraded.yaml",
    "removed": "configs/paper/assurance_degraded_removed.yaml",
}


def _serializable_metric(metric):
    return {
        "gamma": metric.gamma,
        "area_m2": metric.area_m2,
        "worst_case_radius_m": metric.worst_case_radius_m,
        "max_assurance": metric.max_assurance,
        "max_position": {"x_m": metric.max_position.x_m, "y_m": metric.max_position.y_m},
        "reference_assurance": metric.reference_assurance,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/paper-assurance"))
    parser.add_argument("--extent-m", type=float, default=4.0)
    parser.add_argument("--step-m", type=float, default=0.02)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    xs = np.arange(-args.extent_m, args.extent_m + args.step_m / 2, args.step_m)
    ys = xs.copy()
    gamma_values = (0.90, 0.99, 0.999)
    all_metrics = {}

    for name, config_path in SCENARIOS.items():
        deployment = load_assurance_deployment(config_path)
        assurance = assurance_grid(deployment, xs, ys)
        deterministic = deterministic_grid(deployment, xs, ys)
        np.savez_compressed(
            args.output / f"{name}.npz",
            x_m=xs,
            y_m=ys,
            assurance=assurance,
            deterministic=deterministic,
        )
        all_metrics[name] = {
            str(gamma): _serializable_metric(
                region_metrics(assurance, xs, ys, gamma, Position(0.0, 0.0))
            )
            for gamma in gamma_values
        }

    # Degradation sweep: change only east-verifier sigma.
    base = load_assurance_deployment(SCENARIOS["healthy"])
    rows = []
    from qorchsim.assurance.models import AssuranceDeployment, GaussianTimingError, VerifierTimingModel
    from qorchsim.assurance.field import joint_assurance
    for sigma_ns in (1, 2, 3, 4, 5):
        changed = []
        for verifier in base.verifiers:
            changed.append(
                VerifierTimingModel(
                    verifier.verifier_id,
                    verifier.position,
                    verifier.deadline_ps,
                    verifier.deterministic_offset_ps,
                    GaussianTimingError(sigma_ns * 1000.0)
                    if verifier.verifier_id == "v_east"
                    else verifier.error_model,
                )
            )
        deployment = AssuranceDeployment(tuple(changed), base.propagation_speed_m_s)
        grid = assurance_grid(deployment, xs, ys)
        metric = region_metrics(grid, xs, ys, 0.99, Position(0.0, 0.0))
        rows.append(
            {
                "east_sigma_ns": sigma_ns,
                "reference_assurance": joint_assurance(deployment, Position(0.0, 0.0)),
                "max_assurance": metric.max_assurance,
                "max_x_m": metric.max_position.x_m,
                "max_y_m": metric.max_position.y_m,
                "area_0.99_m2": metric.area_m2,
                "worst_radius_0.99_m": metric.worst_case_radius_m,
            }
        )
    with (args.output / "degradation_sweep.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Repetition curves on an x-axis cut through the degraded deployment.
    degraded = load_assurance_deployment(SCENARIOS["degraded"])
    cut_x = np.linspace(-3.0, 3.0, 1201)
    single = np.array([joint_assurance(degraded, Position(float(x), 0.0)) for x in cut_x])
    repetition = {"x_m": cut_x, "single_round": single}
    for rounds in (10, 50, 100):
        threshold = int(np.ceil(0.9 * rounds))
        repetition[f"N{rounds}"] = np.array(
            [session_assurance(float(p), rounds, threshold) for p in single]
        )
    np.savez_compressed(args.output / "repetition.npz", **repetition)

    (args.output / "metrics.json").write_text(
        json.dumps(all_metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "study": "MILCOM spatial assurance",
                "extent_m": args.extent_m,
                "step_m": args.step_m,
                "gamma_values": list(gamma_values),
                "scenarios": SCENARIOS,
                "note": "Synthetic Gaussian timing parameters; not empirical calibration data.",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(f"Wrote paper data to {args.output}")


if __name__ == "__main__":
    main()
