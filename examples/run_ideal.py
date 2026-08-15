"""Run the ideal QPV scenario from Python."""

from pathlib import Path

from qorchsim.config.loader import load_config
from qorchsim.experiments.runner import run_experiment

config = load_config(Path(__file__).parents[1] / "configs" / "qpv_ideal.yaml")
artifacts = run_experiment(config, output_directory="runs/example-ideal")
print(artifacts.run_id)
print(artifacts.summary)
