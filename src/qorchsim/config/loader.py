"""YAML configuration loading."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from qorchsim.config.models import QOrchSimConfig
from qorchsim.errors import ConfigurationError


def load_config(path: str | Path) -> QOrchSimConfig:
    """Load and validate one configuration file."""
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ConfigurationError("top-level YAML must be a mapping")
        return QOrchSimConfig.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError(str(exc)) from exc
