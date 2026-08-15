from pathlib import Path

import yaml
from typer.testing import CliRunner

from qorchsim.cli import app
from qorchsim.config.models import QOrchSimConfig
from qorchsim.experiments.runner import run_experiment
from qorchsim.experiments.summary import summarize_run
from qorchsim.experiments.sweep import expand_sweep, run_sweep


def test_summary_and_inspect_commands(ideal_raw: dict, tmp_path: Path) -> None:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 2
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    config = QOrchSimConfig.model_validate(ideal_raw)
    artifacts = run_experiment(config, output_directory=tmp_path / "run")
    summary = summarize_run(artifacts.output_directory)
    assert summary["rounds"] == 2
    runner = CliRunner()
    inspected = runner.invoke(
        app, ["inspect", str(artifacts.output_directory), "--round", "round-000000"]
    )
    assert inspected.exit_code == 0
    assert "EVENT TRACE" in inspected.output
    summarized = runner.invoke(app, ["summarize", str(artifacts.output_directory)])
    assert summarized.exit_code == 0


def test_small_sweep_expands_and_runs(ideal_raw: dict, tmp_path: Path) -> None:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 1
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    ideal_raw["output"]["write_event_ndjson"] = False
    base = tmp_path / "base.yaml"
    base.write_text(yaml.safe_dump(ideal_raw, sort_keys=False), encoding="utf-8")
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        yaml.safe_dump(
            {
                "base_config": "base.yaml",
                "parameters": {"hardware.prover.memory.t2": ["100 us", "1 ms"]},
                "replicates": 1,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    assert len(expand_sweep(sweep)) == 2
    result = run_sweep(sweep, tmp_path / "sweep-output", processes=1)
    assert result["completed"] == 2
    assert result["failed"] == 0
