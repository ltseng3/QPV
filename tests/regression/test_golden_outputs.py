from __future__ import annotations

import hashlib
import json
from pathlib import Path

from qorchsim.config.loader import load_config
from qorchsim.experiments.runner import run_experiment

ROOT = Path(__file__).parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_portable_golden_artifacts(tmp_path: Path) -> None:
    """Guard canonical artifacts for three representative ten-round scenarios."""
    expected = json.loads(
        (ROOT / "tests" / "fixtures" / "golden_artifacts.json").read_text(encoding="utf-8")
    )
    sources = {
        "ideal": ROOT / "configs" / "qpv_smoke.yaml",
        "schedule_skew": ROOT / "configs" / "attacks" / "schedule_skew.yaml",
        "intercept_resend": ROOT / "configs" / "attacks" / "intercept_resend.yaml",
    }
    for name, source in sources.items():
        config = load_config(source)
        config = config.model_copy(
            update={
                "execution": config.execution.model_copy(update={"model": "portable_qpv"}),
                "simulation": config.simulation.model_copy(update={"rounds": 10}),
                "protocol": config.protocol.model_copy(update={"minimum_committed_rounds": 1}),
            }
        )
        output = tmp_path / name
        run_experiment(config, output_directory=output)
        actual = {
            filename: _sha256(output / filename)
            for filename in ("events.ndjson", "rounds.csv", "summary.json")
        }
        assert actual == expected[name]
