"""Streaming NDJSON trace persistence."""

from __future__ import annotations

import json
from pathlib import Path

from qorchsim.errors import TraceSerializationError
from qorchsim.tracing.events import TraceEvent


class NdjsonTraceSink:
    """Write one canonical JSON object per line without retaining events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", newline="\n")

    def append(self, event: TraceEvent) -> None:
        try:
            self._file.write(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")))
            self._file.write("\n")
        except (TypeError, ValueError) as exc:
            raise TraceSerializationError(str(exc)) from exc

    def close(self) -> None:
        self._file.flush()
        self._file.close()
