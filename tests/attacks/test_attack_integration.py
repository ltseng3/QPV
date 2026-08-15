from pathlib import Path

import pandas as pd

from qorchsim.config.models import QOrchSimConfig
from qorchsim.experiments.runner import run_experiment


def _base(ideal_raw: dict, tmp_path: Path, rounds: int = 20) -> dict:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = rounds
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    ideal_raw["protocol"]["maximum_qber"] = 1.0
    ideal_raw["output"]["directory"] = str(tmp_path / "run")
    ideal_raw["output"]["trace_level"] = "summary"
    ideal_raw["output"]["write_event_ndjson"] = False
    return ideal_raw


def test_early_basis_produces_negative_physical_margin(ideal_raw: dict, tmp_path: Path) -> None:
    raw = _base(ideal_raw, tmp_path, 4)
    raw["attacks"] = [{"type": "schedule_skew", "id": "skew", "x_shift": "-6 us", "y_shift": "-6 us"}]
    artifacts = run_experiment(QOrchSimConfig.model_validate(raw), output_directory=tmp_path / "skew")
    frame = pd.read_csv(artifacts.output_directory / "rounds.csv")
    assert frame["commitment_physical_margin_ps"].lt(0).all()


def test_timestamp_forgery_detected_by_security_policy(ideal_raw: dict, tmp_path: Path) -> None:
    raw = _base(ideal_raw, tmp_path, 5)
    raw["controller"]["policy"] = "security_aware"
    raw["attacks"] = [{
        "type": "timestamp_forgery",
        "id": "forge",
        "node_id": "v0",
        "bias": "-2 us",
        "fields": ["answer_arrival"],
    }]
    artifacts = run_experiment(QOrchSimConfig.model_validate(raw), output_directory=tmp_path / "forge")
    frame = pd.read_csv(artifacts.output_directory / "rounds.csv")
    assert (~frame["accepted"]).all()
    assert frame["reason_codes"].str.contains("timestamp_inconsistency").all()


def test_intercept_resend_qber_is_near_quarter(ideal_raw: dict, tmp_path: Path) -> None:
    raw = _base(ideal_raw, tmp_path, 500)
    raw["attacks"] = [{
        "type": "intercept_resend",
        "id": "imr",
        "position_m": -500,
        "basis_strategy": "random",
        "processing_latency": "100 ns",
        "preparation_latency": "50 ns",
        "replacement_source_fidelity": 1.0,
    }]
    artifacts = run_experiment(QOrchSimConfig.model_validate(raw), output_directory=tmp_path / "imr")
    qber = artifacts.summary["security"]["qber"]
    assert 0.18 <= qber <= 0.32
