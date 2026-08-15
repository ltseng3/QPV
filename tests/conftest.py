from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from qorchsim.config.models import QOrchSimConfig

ROOT = Path(__file__).parents[1]


@pytest.fixture
def ideal_raw() -> dict:
    return yaml.safe_load((ROOT / "configs" / "qpv_ideal.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def portable_config(ideal_raw: dict, tmp_path: Path) -> QOrchSimConfig:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 5
    ideal_raw["protocol"]["minimum_committed_rounds"] = 4
    ideal_raw["output"]["directory"] = str(tmp_path / "run")
    ideal_raw["output"]["trace_level"] = "full"
    return QOrchSimConfig.model_validate(ideal_raw)
