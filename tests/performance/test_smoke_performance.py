import time

import pytest

from qorchsim.config.models import QOrchSimConfig
from qorchsim.experiments.runner import run_experiment


@pytest.mark.performance
def test_one_hundred_rounds_complete_reasonably(ideal_raw: dict, tmp_path) -> None:
    ideal_raw["execution"]["model"] = "portable_qpv"
    ideal_raw["simulation"]["rounds"] = 100
    ideal_raw["protocol"]["minimum_committed_rounds"] = 1
    ideal_raw["output"] = {
        "directory": str(tmp_path / "run"),
        "trace_level": "none",
        "write_round_csv": False,
        "write_event_ndjson": False,
    }
    start = time.perf_counter()
    run_experiment(QOrchSimConfig.model_validate(ideal_raw), output_directory=tmp_path / "run")
    assert time.perf_counter() - start < 20
