"""Canonical configuration serialization."""

from __future__ import annotations

import hashlib
import json

from qorchsim.config.models import QOrchSimConfig


def normalized_dict(config: QOrchSimConfig) -> dict[str, object]:
    """Return a JSON-safe canonical configuration."""
    return config.model_dump(mode="json")


def configuration_hash(config: QOrchSimConfig) -> str:
    material = json.dumps(normalized_dict(config), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(material).hexdigest()
