"""SeQUeNCe entity that dispatches immutable domain events."""

from __future__ import annotations

from sequence.kernel.entity import ClassicalEntity  # type: ignore[import-untyped]

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent
from qorchsim.errors import DuplicateEventError


class SequenceEventPump(ClassicalEntity):
    """Bridge SeQUeNCe ``Process`` calls to the QOrchSim event bus."""

    def __init__(self, name: str, timeline, event_bus: EventBus) -> None:
        super().__init__(name, timeline)
        self.event_bus = event_bus
        self.registry: dict[str, DomainEvent] = {}

    def init(self) -> None:
        """No initialization events are required."""

    def register(self, event: DomainEvent) -> None:
        if event.event_id in self.registry:
            raise DuplicateEventError(event.event_id)
        self.registry[event.event_id] = event

    def dispatch(self, event_id: str) -> None:
        event = self.registry.pop(event_id)
        self.event_bus.publish(event)
