from pathlib import Path

import yaml
from typer.testing import CliRunner

from qorchsim.cli import app


def test_validate_and_run_cli(ideal_raw: dict, tmp_path: Path) -> None:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 2
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(ideal_raw, sort_keys=False), encoding="utf-8")
    runner = CliRunner()
    validated = runner.invoke(app, ["validate", str(config_path)])
    assert validated.exit_code == 0, validated.output
    output = tmp_path / "output"
    executed = runner.invoke(app, ["run", str(config_path), "--output", str(output)])
    assert executed.exit_code == 0, executed.output
    assert (output / "summary.json").exists()
