import pytest
from pydantic import ValidationError

from qorchsim.config.models import QOrchSimConfig, parse_duration_ps
from qorchsim.config.validation import validate_execution_horizon
from qorchsim.errors import ConfigurationError


def test_duration_parser() -> None:
    assert parse_duration_ps("2 us") == 2_000_000
    assert parse_duration_ps("1.5 ns") == 1_500


def test_unknown_field_is_rejected(ideal_raw: dict) -> None:
    ideal_raw["simulation"]["surprise"] = True
    with pytest.raises(ValidationError):
        QOrchSimConfig.model_validate(ideal_raw)


def test_nonphysical_t2_is_rejected(ideal_raw: dict) -> None:
    ideal_raw["hardware"]["prover"]["memory"]["t1"] = "10 us"
    ideal_raw["hardware"]["prover"]["memory"]["t2"] = "30 us"
    with pytest.raises(ValidationError):
        QOrchSimConfig.model_validate(ideal_raw)


def test_short_horizon_is_rejected(portable_config) -> None:
    bad = portable_config.model_copy(
        update={"simulation": portable_config.simulation.model_copy(update={"stop_time": 1})}
    )
    with pytest.raises(ConfigurationError):
        validate_execution_horizon(bad)
