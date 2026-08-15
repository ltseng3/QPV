#!/usr/bin/env python3
"""Render publication figures from previously generated assurance artifacts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _load(path: Path):
    return np.load(path)


def _save(fig, output: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(output / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_regions(data_dir: Path, output: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.25), sharex=True, sharey=True)
    labels = [
        ("healthy", "(a) Four healthy verifiers"),
        ("degraded", "(b) East verifier degraded"),
        ("removed", "(c) Degraded verifier removed"),
    ]
    for ax, (name, title) in zip(axes, labels, strict=True):
        data = _load(data_dir / f"{name}.npz")
        x, y, assurance, deterministic = (
            data["x_m"],
            data["y_m"],
            data["assurance"],
            data["deterministic"],
        )
        ax.contour(x, y, deterministic.astype(float), levels=[0.5], linestyles="--", linewidths=1.0)
        contours = ax.contour(x, y, assurance, levels=[0.90, 0.99, 0.999], linewidths=1.3)
        ax.clabel(contours, inline=True, fontsize=7, fmt=lambda value: f"{value:.3g}")
        ax.scatter([0], [0], marker="x", s=30)
        ax.set_title(title, fontsize=9)
        ax.set_aspect("equal")
        ax.set_xlabel("x (m)")
    axes[0].set_ylabel("y (m)")
    _save(fig, output, "fig_assurance_regions")


def plot_degradation(data_dir: Path, output: Path) -> None:
    rows = []
    with (data_dir / "degradation_sweep.csv").open(encoding="utf-8", newline="") as handle:
        rows.extend(csv.DictReader(handle))
    sigma = np.array([float(r["east_sigma_ns"]) for r in rows])
    center = np.array([float(r["reference_assurance"]) for r in rows])
    maximum = np.array([float(r["max_assurance"]) for r in rows])

    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.plot(sigma, center, marker="o", label=r"$A(p^\star)$")
    ax.plot(sigma, maximum, marker="s", label=r"$\max_p A(p)$")
    ax.axhline(0.99, linestyle="--", linewidth=1.0, label=r"$\gamma=0.99$")
    ax.set_xlabel("East-verifier timing std. dev. (ns)")
    ax.set_ylabel("Timing assurance")
    ax.set_ylim(0.85, 1.005)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    _save(fig, output, "fig_degradation")


def _transition_width(x: np.ndarray, values: np.ndarray) -> float | None:
    # Use the right-hand transition. Interpolate x at probabilities 0.9 and 0.1.
    mask = x >= 0
    xr = x[mask]
    yr = values[mask]
    if yr.max() < 0.9 or yr.min() > 0.1:
        return None
    # yr is expected to fall with x; reverse to interpolate on increasing probability.
    x90 = float(np.interp(0.9, yr[::-1], xr[::-1]))
    x10 = float(np.interp(0.1, yr[::-1], xr[::-1]))
    return abs(x10 - x90)


def plot_repetition(data_dir: Path, output: Path) -> None:
    data = _load(data_dir / "repetition.npz")
    x = data["x_m"]
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    for rounds in (10, 50, 100):
        values = data[f"N{rounds}"]
        width = _transition_width(x, values)
        label = f"N={rounds}"
        if width is not None:
            label += f"  ({width:.2f} m 10–90%)"
        ax.plot(x, values, label=label)
    ax.set_xlabel("Position along degraded-verifier axis, x (m)")
    ax.set_ylabel("Session timing-pass probability")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    _save(fig, output, "fig_repetition")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("runs/paper-assurance"))
    parser.add_argument("--output", type=Path, default=Path("runs/paper-assurance/figures"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plot_regions(args.data, args.output)
    plot_degradation(args.data, args.output)
    plot_repetition(args.data, args.output)
    print(f"Wrote figures to {args.output}")


if __name__ == "__main__":
    main()
