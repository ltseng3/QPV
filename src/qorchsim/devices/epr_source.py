"""Timed EPR-pair source."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from numpy.random import Generator

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.identifiers import stable_id
from qorchsim.core.scheduler import EventScheduler
from qorchsim.devices.capabilities import EprSourceCapabilities
from qorchsim.errors import InvalidDeviceStateError
from qorchsim.quantum.operations import QuantumOperations
from qorchsim.quantum.states import QuantumPairHandle
from qorchsim.types import DurationPs, SimTimePs


class EprSourceState(str, Enum):
    IDLE = "idle"
    GENERATING = "generating"


class EprSource:
    """Exclusive source that completes pair generation at a future event."""

    EVENT_COMPLETE = "device.epr.complete"

    def __init__(
        self,
        source_id: str,
        capabilities: EprSourceCapabilities,
        scheduler: EventScheduler,
        bus: EventBus,
        quantum: QuantumOperations,
        rng: Generator,
    ) -> None:
        self.source_id = source_id
        self.capabilities = capabilities
        self.scheduler = scheduler
        self.bus = bus
        self.quantum = quantum
        self.rng = rng
        self.state = EprSourceState.IDLE
        self._callbacks: dict[str, Callable[[QuantumPairHandle | None], None]] = {}
        self._next_available_ps = 0
        bus.subscribe(self.EVENT_COMPLETE, self._on_complete)

    def generate(self, pair_id: str, callback: Callable[[QuantumPairHandle | None], None]) -> None:
        now = int(self.scheduler.now_ps())
        if self.state is not EprSourceState.IDLE or now < self._next_available_ps:
            raise InvalidDeviceStateError(f"source {self.source_id} is busy")
        self.state = EprSourceState.GENERATING
        operation_id = stable_id("epr-op", self.source_id, pair_id, now)
        self._callbacks[operation_id] = callback
        event = DomainEvent(operation_id, self.EVENT_COMPLETE, {"operation_id": operation_id, "pair_id": pair_id})
        self.scheduler.schedule_after(
            self.capabilities.generation_latency_ps,
            EventPhase.DEVICE_COMPLETION,
            event,
        )

    def _on_complete(self, event: DomainEvent) -> None:
        payload = event.payload
        operation_id = str(payload["operation_id"])
        pair_id = str(payload["pair_id"])
        callback = self._callbacks.pop(operation_id)
        success = self.rng.random() < self.capabilities.generation_success_probability
        pair = self.quantum.create_epr_pair(pair_id, self.capabilities.pair_fidelity) if success else None
        now = int(self.scheduler.now_ps())
        period = int(1e12 / self.capabilities.repetition_rate_hz) if self.capabilities.repetition_rate_hz > 0 else 0
        self._next_available_ps = now + period
        self.state = EprSourceState.IDLE
        callback(pair)
