"""Trace sink interfaces and in-memory implementation."""

from __future__ import annotations

from typing import Protocol

from qorchsim.tracing.events import TraceEvent


class TraceSink(Protocol):
    def append(self, event: TraceEvent) -> None: ...
    def close(self) -> None: ...


class NullTraceSink:
    def append(self, event: TraceEvent) -> None:
        pass

    def close(self) -> None:
        pass


class MemoryTraceSink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, event: TraceEvent) -> None:
        self.events.append(event)

    def close(self) -> None:
        pass
