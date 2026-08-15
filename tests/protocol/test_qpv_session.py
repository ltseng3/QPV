import csv
from pathlib import Path

import pandas as pd

from qorchsim.experiments.runner import run_experiment


def test_ideal_session_accepts_and_traces(portable_config, tmp_path: Path) -> None:
    artifacts = run_experiment(portable_config, output_directory=tmp_path / "ideal")
    assert artifacts.summary["security"]["session_accepted"]
    assert artifacts.summary["security"]["qber"] == 0
    frame = pd.read_csv(artifacts.output_directory / "rounds.csv")
    assert frame["accepted"].all()
    assert frame["commitment_physical_margin_ps"].gt(0).all()
    trace = (artifacts.output_directory / "events.ndjson").read_text(encoding="utf-8")
    assert "quantum_arrival" in trace
    assert "round_complete" in trace


def test_same_seed_is_byte_deterministic(portable_config, tmp_path: Path) -> None:
    first = run_experiment(portable_config, output_directory=tmp_path / "first")
    second = run_experiment(portable_config, output_directory=tmp_path / "second")
    assert (first.output_directory / "events.ndjson").read_bytes() == (
        second.output_directory / "events.ndjson"
    ).read_bytes()
    assert (first.output_directory / "rounds.csv").read_bytes() == (
        second.output_directory / "rounds.csv"
    ).read_bytes()


def test_ideal_controller_and_physical_commitment_margins_agree(portable_config, tmp_path):
    config = portable_config.model_copy(
        update={
            "simulation": portable_config.simulation.model_copy(update={"rounds": 1}),
            "protocol": portable_config.protocol.model_copy(update={"minimum_committed_rounds": 1}),
        }
    )
    artifacts = run_experiment(config, output_directory=tmp_path / "margins")
    with (artifacts.output_directory / "rounds.csv").open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert int(row["commitment_controller_margin_ps"]) == int(
        row["commitment_physical_margin_ps"]
    )


def test_qnd_miss_releases_round_resources_before_next_round(portable_config, tmp_path) -> None:
    """A no-commitment round must not leave the one-slot verifier memory occupied."""
    qnd = portable_config.hardware.prover.qnd.model_copy(update={"efficiency": 0.0})
    prover = portable_config.hardware.prover.model_copy(update={"qnd": qnd})
    hardware = portable_config.hardware.model_copy(update={"prover": prover})
    simulation = portable_config.simulation.model_copy(update={"rounds": 3})
    protocol = portable_config.protocol.model_copy(update={"minimum_committed_rounds": 0})
    config = portable_config.model_copy(
        update={
            "hardware": hardware,
            "simulation": simulation,
            "protocol": protocol,
            "output": portable_config.output.model_copy(update={"directory": str(tmp_path / "misses")}),
        }
    )

    artifacts = run_experiment(config, output_directory=tmp_path / "misses")

    assert artifacts.summary["security"]["rounds"] == 3
    assert artifacts.summary["security"]["committed_rounds"] == 0
