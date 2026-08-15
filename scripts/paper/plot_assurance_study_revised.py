#!/usr/bin/env python3
"""Render the three publication figures for the spatial-assurance paper.

This version is organized around the paper's claims rather than around
raw intermediate outputs:

1. Same deterministic geometry, different operational assurance.
2. Feasibility of a target assurance level versus verifier timing quality.
3. Geographic decision width versus number of repeated QPV rounds.

Expected inputs:
- runs/paper-assurance/healthy.npz
- runs/paper-assurance/degraded.npz
- runs/paper-assurance/removed.npz
- configs/paper/assurance_healthy.yaml

It also uses the analytical assurance package already added in the overlay.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from qorchsim.assurance.field import assurance_grid, joint_assurance
from qorchsim.assurance.io import load_assurance_deployment
from qorchsim.assurance.models import AssuranceDeployment, GaussianTimingError, VerifierTimingModel
from qorchsim.assurance.repetition import session_assurance
from qorchsim.network.geometry import Position


def _save(fig: plt.Figure, output: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(output / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def _load_npz(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(path)
    return data["x_m"], data["y_m"], data["assurance"], data["deterministic"]


def _scenario_panel(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    assurance: np.ndarray,
    deterministic: np.ndarray,
    title: str,
    show_empty_note: bool = False,
) -> None:
    """Plot one operational-assurance panel with identical style/scale."""
    ax.contour(
        x,
        y,
        deterministic.astype(float),
        levels=[0.5],
        linestyles="--",
        linewidths=1.1,
    )
    levels = [0.90, 0.99, 0.999]
    finite_max = float(np.max(assurance))
    levels_to_plot = [level for level in levels if level < finite_max]
    if levels_to_plot:
        cs = ax.contour(x, y, assurance, levels=levels_to_plot, linewidths=1.35)
        ax.clabel(cs, inline=True, fontsize=7, fmt=lambda value: f"{value:.3g}")
    if show_empty_note and finite_max < 0.99:
        ax.text(
            0.02,
            0.96,
            r"$\Omega_{0.99}=\varnothing$",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", alpha=0.15),
        )
    ax.scatter([0.0], [0.0], marker="x", s=36)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("x (m)")
    ax.set_aspect("equal")
    ax.set_xlim(float(x[0]), float(x[-1]))
    ax.set_ylim(float(y[0]), float(y[-1]))


def plot_operational_tradeoff(data_dir: Path, output: Path) -> None:
    """Figure 1: same geometry, different assurance outcomes."""
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.35), sharex=True, sharey=True)

    items = [
        ("healthy", "(a) Four healthy verifiers", False),
        ("degraded", "(b) East verifier degraded", True),
        ("removed", "(c) Degraded verifier removed", False),
    ]
    for ax, (name, title, empty_note) in zip(axes, items, strict=True):
        x, y, assurance, deterministic = _load_npz(data_dir / f"{name}.npz")
        _scenario_panel(ax, x, y, assurance, deterministic, title, show_empty_note=empty_note)

    axes[0].set_ylabel("y (m)")
    fig.suptitle(
        "Operational timing assurance for the tactical-gateway case study",
        fontsize=10,
        y=1.02,
    )
    _save(fig, output, "fig1_operational_assurance")


def _healthy_base_deployment(config_dir: Path) -> AssuranceDeployment:
    return load_assurance_deployment(config_dir / "assurance_healthy.yaml")


def _replace_east_sigma(
    base: AssuranceDeployment,
    east_sigma_ns: float,
) -> AssuranceDeployment:
    new_verifiers: list[VerifierTimingModel] = []
    for verifier in base.verifiers:
        if verifier.verifier_id == "v_east":
            new_verifiers.append(
                VerifierTimingModel(
                    verifier_id=verifier.verifier_id,
                    position=verifier.position,
                    deadline_ps=verifier.deadline_ps,
                    deterministic_offset_ps=verifier.deterministic_offset_ps,
                    error_model=GaussianTimingError(stddev_ps=east_sigma_ns * 1000.0),
                )
            )
        else:
            new_verifiers.append(verifier)
    return AssuranceDeployment(tuple(new_verifiers), base.propagation_speed_m_s)


def _dense_max_assurance(
    deployment: AssuranceDeployment,
    extent_m: float = 4.0,
    step_m: float = 0.02,
) -> float:
    axis = np.arange(-extent_m, extent_m + step_m / 2, step_m)
    assurance = assurance_grid(deployment, axis, axis)
    return float(np.max(assurance))


def plot_feasibility_vs_jitter(config_dir: Path, output: Path) -> None:
    """Figure 2: requested assurance becomes infeasible as one verifier degrades."""
    base = _healthy_base_deployment(config_dir)

    sigma_ns = np.linspace(1.0, 5.0, 81)
    center_assurance = []
    max_assurance = []
    p_star = Position(0.0, 0.0)

    for sigma in sigma_ns:
        deployment = _replace_east_sigma(base, float(sigma))
        center_assurance.append(joint_assurance(deployment, p_star))
        max_assurance.append(_dense_max_assurance(deployment))

    center_assurance = np.asarray(center_assurance, dtype=float)
    max_assurance = np.asarray(max_assurance, dtype=float)

    target = 0.99
    sigma_crit = None
    below = np.where(max_assurance < target)[0]
    if len(below) > 0:
        hi = int(below[0])
        if hi > 0:
            lo = hi - 1
            sigma_crit = float(
                np.interp(
                    target,
                    [max_assurance[hi], max_assurance[lo]],
                    [sigma_ns[hi], sigma_ns[lo]],
                )
            )

    fig = plt.figure(figsize=(5.2, 3.6))
    ax = fig.add_subplot(111)
    ax.plot(sigma_ns, center_assurance, linewidth=1.5, label=r"$A(p^\star)$")
    ax.plot(sigma_ns, max_assurance, linewidth=1.5, label=r"$\max_{p} A(p)$")
    ax.axhline(target, linestyle="--", linewidth=1.0, label=r"target $\gamma=0.99$")
    if sigma_crit is not None:
        ax.axvline(sigma_crit, linestyle=":", linewidth=1.0)
        ax.annotate(
            rf"$\sigma_{{\rm crit}}\approx {sigma_crit:.2f}$ ns",
            xy=(sigma_crit, target),
            xytext=(sigma_crit + 0.15, target - 0.03),
            arrowprops=dict(arrowstyle="->", lw=0.8),
            fontsize=8,
        )
    ax.set_xlabel("East-verifier residual timing std. dev. (ns)")
    ax.set_ylabel("Timing assurance")
    ax.set_ylim(0.88, 1.005)
    ax.set_xlim(float(sigma_ns[0]), float(sigma_ns[-1]))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower left")
    _save(fig, output, "fig2_feasibility_vs_jitter")


def _single_round_cut_for_degraded(config_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    deployment = load_assurance_deployment(config_dir / "assurance_degraded.yaml")
    x_cut = np.linspace(-3.0, 3.0, 1601)
    single = np.array(
        [joint_assurance(deployment, Position(float(x), 0.0)) for x in x_cut],
        dtype=float,
    )
    return x_cut, single


def _transition_width(
    xvals: np.ndarray,
    probabilities: np.ndarray,
    low: float = 0.1,
    high: float = 0.9,
) -> float | None:
    """Return the right-side geographic transition width between two probabilities."""
    mask = xvals >= 0.0
    xr = xvals[mask]
    yr = probabilities[mask]
    if yr.max() < high or yr.min() > low:
        return None
    x_high = float(np.interp(high, yr[::-1], xr[::-1]))
    x_low = float(np.interp(low, yr[::-1], xr[::-1]))
    return abs(x_low - x_high)


def plot_rounds_vs_width(config_dir: Path, output: Path) -> None:
    """Figure 3: more rounds shrink the ambiguous geographic transition band."""
    x_cut, single_round = _single_round_cut_for_degraded(config_dir)

    round_counts = np.array([10, 20, 50, 100, 200], dtype=int)
    widths = []
    for rounds in round_counts:
        minimum_successes = math.ceil(0.9 * rounds)
        session = np.array(
            [
                session_assurance(float(probability), int(rounds), minimum_successes)
                for probability in single_round
            ],
            dtype=float,
        )
        width = _transition_width(x_cut, session)
        widths.append(np.nan if width is None else width)

    widths = np.asarray(widths, dtype=float)

    fig = plt.figure(figsize=(5.0, 3.4))
    ax = fig.add_subplot(111)
    ax.plot(round_counts, widths, marker="o", linewidth=1.4)
    for rounds, width in zip(round_counts, widths, strict=True):
        ax.annotate(f"{width:.2f} m", (rounds, width), textcoords="offset points", xytext=(0, 6),
                    ha="center", fontsize=8)
    ax.set_xlabel("Number of QPV rounds, $N$")
    ax.set_ylabel("10–90% transition width (m)")
    ax.set_title("Repeated rounds sharpen the spatial decision", fontsize=10)
    ax.grid(alpha=0.25)
    _save(fig, output, "fig3_rounds_vs_width")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("runs/paper-assurance"))
    parser.add_argument("--config-dir", type=Path, default=Path("configs/paper"))
    parser.add_argument("--output", type=Path, default=Path("runs/paper-assurance/figures"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    plot_operational_tradeoff(args.data, args.output)
    plot_feasibility_vs_jitter(args.config_dir, args.output)
    plot_rounds_vs_width(args.config_dir, args.output)
    print(f"Wrote figures to {args.output}")


if __name__ == "__main__":
    main()
