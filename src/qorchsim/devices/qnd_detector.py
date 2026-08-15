"""Abstract timed quantum non-demolition presence detector."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from numpy.random import Generator

from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.identifiers import stable_id
from qorchsim.core.scheduler import EventScheduler
from qorchsim.devices.capabilities import QndCapabilities
from qorchsim.quantum.kraus import depolarizing
from qorchsim.quantum.operations import QuantumOperations
from qorchsim.quantum.states import QuantumHandle
from qorchsim.types import DurationPs, SimTimePs


class QndOutcome(str, Enum):
    VALID_DETECTION = "valid_detection"
    MISSED_PHOTON = "missed_photon"
    DARK_COUNT = "dark_count"
    STATE_DESTROYED = "state_destroyed"
    OUTSIDE_GATE = "outside_gate"
    DETECTOR_BUSY = "detector_busy"


@dataclass(frozen=True, slots=True)
class QndResult:
    outcome: QndOutcome
    qubit: QuantumHandle | None


@dataclass
class _Gate:
    gate_id: str
    opens_ps: int
    closes_ps: int
    callback: Callable[[QndResult], None]
    resolved: bool = False
    photon: QuantumHandle | None = None


class QndDetector:
    """Probabilistic presence detection with gate and dead-time semantics."""

    EVENT_COMPLETE = "device.qnd.complete"
    EVENT_GATE_CLOSE = "device.qnd.gate_close"

    def __init__(
        self,
        detector_id: str,
        capabilities: QndCapabilities,
        scheduler: EventScheduler,
        bus: EventBus,
        quantum: QuantumOperations,
        rng: Generator,
    ) -> None:
        self.detector_id = detector_id
        self.capabilities = capabilities
        self.scheduler = scheduler
        self.bus = bus
        self.quantum = quantum
        self.rng = rng
        self._gates: dict[str, _Gate] = {}
        self._busy_until_ps = 0
        bus.subscribe(self.EVENT_COMPLETE, self._on_complete)
        bus.subscribe(self.EVENT_GATE_CLOSE, self._on_gate_close)

    def open_gate(
        self,
        gate_id: str,
        opens_ps: SimTimePs,
        callback: Callable[[QndResult], None],
    ) -> None:
        opens = int(opens_ps)
        closes = opens + int(self.capabilities.gate_width_ps)
        gate = _Gate(gate_id, opens, closes, callback)
        self._gates[gate_id] = gate
        self.scheduler.schedule_at(
            SimTimePs(closes),
            EventPhase.TIMEOUT,
            DomainEvent(stable_id("qnd-close", gate_id), self.EVENT_GATE_CLOSE, {"gate_id": gate_id}),
        )

    def photon_arrival(self, gate_id: str, qubit: QuantumHandle) -> None:
        gate = self._gates.get(gate_id)
        now = int(self.scheduler.now_ps())
        if gate is None or gate.resolved:
            return
        if now < gate.opens_ps or now > gate.closes_ps:
            gate.resolved = True
            gate.callback(QndResult(QndOutcome.OUTSIDE_GATE, None))
            return
        if now < self._busy_until_ps:
            gate.resolved = True
            gate.callback(QndResult(QndOutcome.DETECTOR_BUSY, None))
            return
        gate.photon = qubit
        operation_id = stable_id("qnd", self.detector_id, gate_id, now)
        self.scheduler.schedule_after(
            self.capabilities.operation_latency_ps,
            EventPhase.DEVICE_COMPLETION,
            DomainEvent(operation_id, self.EVENT_COMPLETE, {"gate_id": gate_id}),
        )

    def _on_complete(self, event: DomainEvent) -> None:
        gate = self._gates.get(str(event.payload["gate_id"]))
        if gate is None or gate.resolved:
            return
        gate.resolved = True
        self._busy_until_ps = int(self.scheduler.now_ps()) + int(self.capabilities.dead_time_ps)
        if self.rng.random() >= self.capabilities.detection_efficiency:
            gate.callback(QndResult(QndOutcome.MISSED_PHOTON, None))
            return
        if self.rng.random() >= self.capabilities.state_survival_probability:
            gate.callback(QndResult(QndOutcome.STATE_DESTROYED, None))
            return
        if gate.photon is not None and self.rng.random() < self.capabilities.disturbance_probability:
            self.quantum.apply_kraus(gate.photon, depolarizing(1.0))
        gate.callback(QndResult(QndOutcome.VALID_DETECTION, gate.photon))

    def _on_gate_close(self, event: DomainEvent) -> None:
        gate = self._gates.get(str(event.payload["gate_id"]))
        if gate is None or gate.resolved:
            return
        gate.resolved = True
        width_seconds = int(self.capabilities.gate_width_ps) / 1e12
        dark_probability = 1.0 - math.exp(-self.capabilities.dark_count_rate_hz * width_seconds)
        outcome = QndOutcome.DARK_COUNT if self.rng.random() < dark_probability else QndOutcome.MISSED_PHOTON
        gate.callback(QndResult(outcome, None))
