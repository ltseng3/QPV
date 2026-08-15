from pathlib import Path

import pandas as pd

from qorchsim.config.models import QOrchSimConfig
from qorchsim.experiments.runner import run_experiment


def test_security_policy_rejects_poisoned_telemetry_preflight(ideal_raw: dict, tmp_path: Path) -> None:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 3
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    ideal_raw["controller"]["policy"] = "security_aware"
    ideal_raw["controller"]["maximum_reported_t2"] = "50 us"
    ideal_raw["attacks"] = [{
        "type": "telemetry_poisoning",
        "id": "poison",
        "resource_id": "prover.memory",
        "fields": {"t2_ps": 100_000_000},
    }]
    artifacts = run_experiment(
        QOrchSimConfig.model_validate(ideal_raw), output_directory=tmp_path / "telemetry"
    )
    frame = pd.read_csv(artifacts.output_directory / "rounds.csv")
    assert (~frame["accepted"]).all()
    assert frame["reason_codes"].str.contains("reported_t2").all()


def test_security_policy_rejects_visible_unsafe_schedule(ideal_raw: dict, tmp_path: Path) -> None:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 2
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    ideal_raw["controller"]["policy"] = "security_aware"
    ideal_raw["attacks"] = [{
        "type": "schedule_skew",
        "id": "visible-skew",
        "x_shift": "-6 us",
        "y_shift": "-6 us",
        "modify_controller_view": True,
    }]
    artifacts = run_experiment(
        QOrchSimConfig.model_validate(ideal_raw), output_directory=tmp_path / "schedule"
    )
    frame = pd.read_csv(artifacts.output_directory / "rounds.csv")
    assert (~frame["accepted"]).all()
    assert frame["reason_codes"].str.contains("delta_out_of_bounds").all()
