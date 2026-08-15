"""Deterministic identifiers."""

from __future__ import annotations

import hashlib


def stable_id(prefix: str, *parts: object, length: int = 16) -> str:
    """Create a deterministic identifier from stable textual parts."""
    material = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()[:length]
    return f"{prefix}-{digest}"
