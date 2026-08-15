"""Timed BB84 measurement device."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from numpy.random import Generator

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.identifiers import stable_id
from qorchsim.core.scheduler import EventScheduler
from qorchsim.devices.capabilities import MeasurementCapabilities
from qorchsim.errors import InvalidDeviceStateError
from qorchsim.quantum.operations import QuantumOperations
from qorchsim.quantum.states import QuantumHandle
from qorchsim.types import DurationPs


class MeasurementState(str, Enum):
    IDLE = "idle"
    BUSY = "busy"


class TimedMeasurementDevice:
    """Measure at operation completion, not request time."""

    EVENT_COMPLETE = "device.measurement.complete"

    def __init__(
        self,
        device_id: str,
        capabilities: MeasurementCapabilities,
        scheduler: EventScheduler,
        bus: EventBus,
        quantum: QuantumOperations,
        rng: Generator,
    ) -> None:
        self.device_id = device_id
        self.capabilities = capabilities
        self.scheduler = scheduler
        self.bus = bus
        self.quantum = quantum
        self.rng = rng
        self.state = MeasurementState.IDLE
        self._pending: dict[str, tuple[QuantumHandle, int, Callable[[int], None]]] = {}
        self._available_at_ps = 0
        bus.subscribe(self.EVENT_COMPLETE, self._on_complete)

    def measure(self, qubit: QuantumHandle, basis: int, callback: Callable[[int], None]) -> None:
        now = int(self.scheduler.now_ps())
        if self.state is not MeasurementState.IDLE or now < self._available_at_ps:
            raise InvalidDeviceStateError(f"measurement device {self.device_id} is busy")
        self.state = MeasurementState.BUSY
        operation_id = stable_id("measure", self.device_id, qubit.qubit_id, basis, now)
        self._pending[operation_id] = (qubit, basis, callback)
        delay = DurationPs(
            int(self.capabilities.basis_switch_latency_ps) + int(self.capabilities.measurement_latency_ps)
        )
        self.scheduler.schedule_after(
            delay,
            EventPhase.DEVICE_COMPLETION,
            DomainEvent(operation_id, self.EVENT_COMPLETE, {"operation_id": operation_id}),
        )

    def _on_complete(self, event: DomainEvent) -> None:
        operation_id = str(event.payload["operation_id"])
        pending = self._pending.pop(operation_id, None)
        if pending is None:
            return
        qubit, basis, callback = pending
        result = self.quantum.measure_bb84(qubit, basis, self.rng)
        if self.rng.random() > self.capabilities.measurement_fidelity:
            result ^= 1
        self.state = MeasurementState.IDLE
        self._available_at_ps = int(self.scheduler.now_ps()) + int(self.capabilities.dead_time_ps)
        callback(result)
