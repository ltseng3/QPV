"""Ordered synchronous domain event bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, Protocol

from qorchsim.core.events import DomainEvent
from qorchsim.errors import DuplicateEventError


class EventHandler(Protocol):
    """Handler port for domain events."""

    def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""


Handler = EventHandler | Callable[[DomainEvent], None]


class EventBus:
    """Publish events in deterministic subscription order."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler, *, allow_duplicate: bool = False) -> None:
        handlers = self._handlers[event_type]
        if not allow_duplicate and any(existing is handler for existing in handlers):
            raise DuplicateEventError(f"handler already registered for {event_type}")
        handlers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in tuple(self._handlers.get(event.event_type, ())):
            if callable(handler) and not hasattr(handler, "handle"):
                handler(event)
            else:
                handler.handle(event)  # type: ignore[union-attr]

    def subscriber_count(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, ()))
