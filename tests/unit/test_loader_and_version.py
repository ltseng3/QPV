import importlib.metadata
from pathlib import Path

import pytest

from qorchsim.adapters.sequence.version import check_sequence_version
from qorchsim.config.loader import load_config
from qorchsim.errors import ConfigurationError


def test_loader_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_config(path)


def test_version_guard_can_record_missing_package(monkeypatch) -> None:
    def missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    version, warnings = check_sequence_version(allow_unsupported=True)
    assert version is None
    assert warnings


def test_version_guard_can_allow_other_version(monkeypatch) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
    version, warnings = check_sequence_version(allow_unsupported=True)
    assert version == "9.9.9"
    assert "expected SeQUeNCe" in warnings[0]
