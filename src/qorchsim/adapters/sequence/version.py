"""Strict SeQUeNCe version guard."""

from __future__ import annotations

import importlib.metadata

from qorchsim.errors import UnsupportedSequenceVersionError

SUPPORTED_SEQUENCE_VERSION = "1.0.0"


def check_sequence_version(*, allow_unsupported: bool = False) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    try:
        version = importlib.metadata.version("sequence")
    except importlib.metadata.PackageNotFoundError as exc:
        if allow_unsupported:
            warnings.append("SeQUeNCe package is not installed; portable backend was requested")
            return None, warnings
        raise UnsupportedSequenceVersionError(
            "SeQUeNCe 1.0.0 is required. Install with `pip install sequence==1.0.0`."
        ) from exc
    if version != SUPPORTED_SEQUENCE_VERSION:
        message = f"expected SeQUeNCe {SUPPORTED_SEQUENCE_VERSION}, found {version}"
        if not allow_unsupported:
            raise UnsupportedSequenceVersionError(message)
        warnings.append(message)
    return version, warnings
