"""Timed single-qubit memory with T1/T2 noise."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from numpy.random import Generator

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.identifiers import stable_id
from qorchsim.core.scheduler import EventScheduler
from qorchsim.devices.capabilities import MemoryCapabilities
from qorchsim.errors import InvalidDeviceStateError
from qorchsim.quantum.noise import memory_channels
from qorchsim.quantum.operations import QuantumOperations
from qorchsim.quantum.states import QuantumHandle


class MemoryState(str, Enum):
    EMPTY = "empty"
    LOADING = "loading"
    STORED = "stored"
    RETRIEVING = "retrieving"
    EXPIRED = "expired"
    FAILED = "failed"


class TimedQuantumMemory:
    """One-slot memory whose physical state changes on operation completion."""

    EVENT_LOAD_COMPLETE = "device.memory.load_complete"
    EVENT_RETRIEVE_COMPLETE = "device.memory.retrieve_complete"
    EVENT_EXPIRE = "device.memory.expire"

    def __init__(
        self,
        memory_id: str,
        capabilities: MemoryCapabilities,
        scheduler: EventScheduler,
        bus: EventBus,
        quantum: QuantumOperations,
        rng: Generator,
    ) -> None:
        self.memory_id = memory_id
        self.capabilities = capabilities
        self.scheduler = scheduler
        self.bus = bus
        self.quantum = quantum
        self.rng = rng
        self.state = MemoryState.EMPTY
        self.qubit: QuantumHandle | None = None
        self.stored_at_ps: int | None = None
        self._load_callbacks: dict[str, Callable[[bool], None]] = {}
        self._retrieve_callbacks: dict[str, Callable[[QuantumHandle | None, int], None]] = {}
        self._pending_qubits: dict[str, QuantumHandle] = {}
        self._generation = 0
        bus.subscribe(self.EVENT_LOAD_COMPLETE, self._on_load_complete)
        bus.subscribe(self.EVENT_RETRIEVE_COMPLETE, self._on_retrieve_complete)
        bus.subscribe(self.EVENT_EXPIRE, self._on_expire)

    def load(self, qubit: QuantumHandle, callback: Callable[[bool], None]) -> None:
        if self.state is not MemoryState.EMPTY:
            raise InvalidDeviceStateError(f"memory {self.memory_id} is {self.state.value}")
        self.state = MemoryState.LOADING
        now = int(self.scheduler.now_ps())
        operation_id = stable_id("memory-load", self.memory_id, qubit.qubit_id, now, self._generation)
        self._generation += 1
        self._pending_qubits[operation_id] = qubit
        self._load_callbacks[operation_id] = callback
        self.scheduler.schedule_after(
            self.capabilities.load_latency_ps,
            EventPhase.DEVICE_COMPLETION,
            DomainEvent(operation_id, self.EVENT_LOAD_COMPLETE, {"operation_id": operation_id}),
        )

    def retrieve(self, callback: Callable[[QuantumHandle | None, int], None]) -> None:
        if self.state is not MemoryState.STORED or self.qubit is None or self.stored_at_ps is None:
            raise InvalidDeviceStateError(f"memory {self.memory_id} has no retrievable qubit")
        self.state = MemoryState.RETRIEVING
        now = int(self.scheduler.now_ps())
        operation_id = stable_id("memory-retrieve", self.memory_id, self.qubit.qubit_id, now, self._generation)
        self._generation += 1
        self._retrieve_callbacks[operation_id] = callback
        self.scheduler.schedule_after(
            self.capabilities.retrieve_latency_ps,
            EventPhase.DEVICE_COMPLETION,
            DomainEvent(operation_id, self.EVENT_RETRIEVE_COMPLETE, {"operation_id": operation_id}),
        )

    def discard(self) -> None:
        self.qubit = None
        self.stored_at_ps = None
        self.state = MemoryState.EMPTY
        self._generation += 1

    def _on_load_complete(self, event: DomainEvent) -> None:
        operation_id = str(event.payload["operation_id"])
        if operation_id not in self._pending_qubits:
            return
        qubit = self._pending_qubits.pop(operation_id)
        callback = self._load_callbacks.pop(operation_id)
        if self.rng.random() >= self.capabilities.load_efficiency:
            self.state = MemoryState.FAILED
            callback(False)
            self.state = MemoryState.EMPTY
            return
        self.qubit = qubit
        self.stored_at_ps = int(self.scheduler.now_ps())
        self.state = MemoryState.STORED
        if self.capabilities.maximum_hold_ps is not None:
            expire_id = stable_id("memory-expire", self.memory_id, qubit.qubit_id, self._generation)
            self.scheduler.schedule_after(
                self.capabilities.maximum_hold_ps,
                EventPhase.TIMEOUT,
                DomainEvent(
                    expire_id,
                    self.EVENT_EXPIRE,
                    {"qubit_id": qubit.qubit_id, "generation": self._generation},
                ),
            )
        callback(True)

    def _on_retrieve_complete(self, event: DomainEvent) -> None:
        operation_id = str(event.payload["operation_id"])
        callback = self._retrieve_callbacks.pop(operation_id, None)
        if callback is None or self.qubit is None or self.stored_at_ps is None:
            return
        qubit = self.qubit
        now = int(self.scheduler.now_ps())
        dwell = now - self.stored_at_ps
        for operators in memory_channels(
            dwell,
            int(self.capabilities.t1_ps) if self.capabilities.t1_ps is not None else None,
            int(self.capabilities.t2_ps) if self.capabilities.t2_ps is not None else None,
        ):
            self.quantum.apply_kraus(qubit, operators)
        success = self.rng.random() < self.capabilities.retrieve_efficiency
        self.qubit = None
        self.stored_at_ps = None
        self.state = MemoryState.EMPTY
        self._generation += 1
        callback(qubit if success else None, dwell)

    def _on_expire(self, event: DomainEvent) -> None:
        payload = event.payload
        if (
            self.state is MemoryState.STORED
            and self.qubit is not None
            and payload["qubit_id"] == self.qubit.qubit_id
            and int(payload["generation"]) == self._generation
        ):
            self.qubit = None
            self.stored_at_ps = None
            self.state = MemoryState.EXPIRED
