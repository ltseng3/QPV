"""Regenerate summaries from persisted round CSV files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def summarize_run(run_directory: str | Path) -> dict[str, object]:
    directory = Path(run_directory)
    frame = pd.read_csv(directory / "rounds.csv")
    compared = frame[frame["measurement_match"].notna()]
    mismatches = int((compared["measurement_match"].astype(str).str.lower() == "false").sum())
    summary = {
        "rounds": int(len(frame)),
        "accepted_rounds": int(frame["accepted"].sum()),
        "committed_rounds": int(frame["committed"].sum()),
        "qber": mismatches / len(compared) if len(compared) else 1.0,
    }
    (directory / "summary.regenerated.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary
