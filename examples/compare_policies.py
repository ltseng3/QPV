"""Compare baseline and security-aware policies under timestamp forgery."""

from pathlib import Path

from qorchsim.config.loader import load_config
from qorchsim.experiments.runner import run_experiment

source = Path(__file__).parents[1] / "configs" / "attacks" / "timestamp_forgery.yaml"
base = load_config(source)
for policy in ("baseline", "security_aware"):
    config = base.model_copy(
        update={
            "controller": base.controller.model_copy(update={"policy": policy}),
            "execution": base.execution.model_copy(update={"model": "portable_qpv"}),
        }
    )
    result = run_experiment(config, output_directory=f"runs/timestamp-{policy}")
    print(policy, result.summary["security"])
