"""Run a small scenario without importing SeQUeNCe.

This is useful for verifying configuration and domain logic. Publication runs should
use ``execution.model: sequence_qpv`` with SeQUeNCe 1.0.0 installed.
"""

from pathlib import Path

from qorchsim.config.loader import load_config
from qorchsim.experiments.runner import run_experiment

config = load_config(Path(__file__).parents[1] / "configs" / "qpv_ideal.yaml")
config = config.model_copy(
    update={
        "execution": config.execution.model_copy(update={"model": "portable_qpv"}),
        "simulation": config.simulation.model_copy(update={"rounds": 10}),
        "protocol": config.protocol.model_copy(update={"minimum_committed_rounds": 9}),
    }
)
artifacts = run_experiment(config, output_directory="runs/example-portable")
print(artifacts.summary)
