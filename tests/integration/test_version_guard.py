import importlib.metadata

import pytest

from qorchsim.adapters.sequence.version import check_sequence_version
from qorchsim.errors import UnsupportedSequenceVersionError


def test_version_guard_rejects_missing_sequence(monkeypatch) -> None:
    def missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(UnsupportedSequenceVersionError):
        check_sequence_version()
