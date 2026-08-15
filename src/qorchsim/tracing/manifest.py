"""Run manifest creation."""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any

from qorchsim import __version__


@dataclass
class RunManifest:
    schema_version: str
    run_id: str
    normalized_config: dict[str, Any]
    master_seed: int
    qorchsim_version: str
    sequence_version: str | None
    python_version: str
    platform: str
    started_at: str
    completed_at: str | None
    event_count: int
    warnings: list[str]
    output_schema_versions: dict[str, str]

    @classmethod
    def start(cls, run_id: str, config: dict[str, Any], seed: int, warnings: list[str]) -> "RunManifest":
        try:
            sequence_version = importlib.metadata.version("sequence")
        except importlib.metadata.PackageNotFoundError:
            sequence_version = None
        return cls(
            schema_version="1.0",
            run_id=run_id,
            normalized_config=config,
            master_seed=seed,
            qorchsim_version=__version__,
            sequence_version=sequence_version,
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            started_at=datetime.now(UTC).isoformat(),
            completed_at=None,
            event_count=0,
            warnings=warnings,
            output_schema_versions={"events": "1.0", "rounds": "1.0", "summary": "1.0"},
        )

    def finish(self, event_count: int) -> None:
        self.event_count = event_count
        self.completed_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
