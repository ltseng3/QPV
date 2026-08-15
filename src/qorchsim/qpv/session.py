"""End-to-end multi-round commitment-QPV simulation runtime."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from numpy.random import Generator

from qorchsim.attacks.base import AttackContext
from qorchsim.attacks.intercept_resend import InterceptResendAttack
from qorchsim.attacks.pipeline import AttackPipeline
from qorchsim.cloudsim.resources import ResourceSnapshot
from qorchsim.config.models import QOrchSimConfig
from qorchsim.config.validation import estimate_round_period_ps
from qorchsim.core.event_bus import EventBus
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.identifiers import stable_id
from qorchsim.core.random_streams import RandomStreams
from qorchsim.core.scheduler import EventScheduler
from qorchsim.devices.capabilities import (
    ClockCapabilities,
    EprSourceCapabilities,
    MeasurementCapabilities,
    MemoryCapabilities,
    QndCapabilities,
)
from qorchsim.devices.epr_source import EprSource
from qorchsim.devices.local_clock import LocalClock
from qorchsim.devices.measurement import TimedMeasurementDevice
from qorchsim.devices.qnd_detector import QndDetector, QndOutcome, QndResult
from qorchsim.devices.quantum_memory import MemoryState, TimedQuantumMemory
from qorchsim.metrics.utilization import UtilizationCounters
from qorchsim.network.classical_channel import AttackableClassicalChannel
from qorchsim.network.geometry import Position, distance, propagation_delay_ps
from qorchsim.network.transmissions import ClassicalTransmission, QuantumTransmission
from qorchsim.qpv.acceptance import (
    AcceptanceThresholds,
    BaselineRoundAcceptance,
    SecurityAwareRoundAcceptance,
    aggregate_session,
)
from qorchsim.qpv.basis import xor_basis
from qorchsim.qpv.messages import MessageType, ProtocolMessage
from qorchsim.qpv.models import RoundResult, SessionResult, VerifierReport
from qorchsim.qpv.plans import RoundPlan
from qorchsim.qpv.timing import commitment_margin_ps, response_margin_ps
from qorchsim.policies.schedule import ScheduleBounds, SchedulePolicy
from qorchsim.policies.telemetry import SecurityTelemetryPolicy, TelemetryBounds
from qorchsim.quantum.kraus import depolarizing
from qorchsim.quantum.operations import QuantumOperations
from qorchsim.quantum.states import QuantumHandle, QuantumPairHandle
from qorchsim.tracing.events import TraceEvent
from qorchsim.tracing.sink import TraceSink


@dataclass
class _VerifierObservation:
    commitment: int | None = None
    commitment_physical_ps: int | None = None
    commitment_local_ps: int | None = None
    answer: int | None = None
    answer_physical_ps: int | None = None
    answer_local_ps: int | None = None
    report_sent: bool = False


@dataclass
class _RoundRuntime:
    original_plan: RoundPlan
    physical_plan: RoundPlan
    rng: Generator
    x: int
    y: int
    pair: QuantumPairHandle | None = None
    challenge: QuantumHandle | None = None
    v0_memory_ready: bool = False
    qnd_outcome: QndOutcome | None = None
    committed: bool = False
    valid_state_commitment: bool = False
    commitment_generated_ps: int | None = None
    x_arrival_ps: int | None = None
    y_arrival_ps: int | None = None
    measurement_started: bool = False
    prover_measurement: int | None = None
    verifier_measurement: int | None = None
    memory_dwell_ps: int | None = None
    observations: dict[str, _VerifierObservation] = field(
        default_factory=lambda: {"v0": _VerifierObservation(), "v1": _VerifierObservation()}
    )
    reports: dict[str, VerifierReport] = field(default_factory=dict)
    completed: bool = False


class QpvSessionRuntime:
    """Coordinate physical devices, protocol messages, attacks, and controller decisions."""

    EVENT_ROUND_START = "qpv.round.start"
    EVENT_CHALLENGE_SEND = "qpv.challenge.send"
    EVENT_QUANTUM_ARRIVAL = "qpv.quantum.arrival"
    EVENT_INTERCEPT_COMPLETE = "qpv.intercept.complete"
    EVENT_REPLACEMENT_SEND = "qpv.replacement.send"
    EVENT_BASIS_SEND = "qpv.basis.send"
    EVENT_ROUND_TIMEOUT = "qpv.round.timeout"
    EVENT_FINAL_TIMEOUT = "qpv.round.final_timeout"

    def __init__(
        self,
        *,
        run_id: str,
        session_id: str,
        config: QOrchSimConfig,
        scheduler: EventScheduler,
        bus: EventBus,
        quantum: QuantumOperations,
        attacks: AttackPipeline,
        resources: ResourceSnapshot,
        random_streams: RandomStreams,
        trace_sink: TraceSink,
    ) -> None:
        self.run_id = run_id
        self.session_id = session_id
        self.config = config
        self.scheduler = scheduler
        self.bus = bus
        self.quantum = quantum
        self.attacks = attacks
        self.resources = resources
        self.random_streams = random_streams
        self.trace_sink = trace_sink
        self.rounds: dict[str, _RoundRuntime] = {}
        self.results: list[RoundResult] = []
        self.counters = UtilizationCounters()
        self.positions = {
            key: Position(value.x_m, value.y_m) for key, value in config.geometry.nodes.items()
        }
        self.preflight_reason_codes: tuple[str, ...] = ()
        if config.controller.policy == "security_aware":
            telemetry_decision = SecurityTelemetryPolicy(
                TelemetryBounds(
                    maximum_t2_ps=(
                        int(config.controller.maximum_reported_t2)
                        if config.controller.maximum_reported_t2 is not None
                        else None
                    ),
                    maximum_calibration_age_ps=int(config.controller.calibration_age_limit),
                )
            ).validate(resources, 0)
            self.preflight_reason_codes = telemetry_decision.reason_codes
        self.quantum_link = config.links.quantum[0]
        self.classical_links = {(link.source, link.destination): link for link in config.links.classical}
        self.intercept_attack = next(
            (attack for attack in attacks.attacks if isinstance(attack, InterceptResendAttack)), None
        )
        self._trace_sequence = 0

        self.source = self._build_source()
        self.prover_memory = self._build_memory("prover.memory", config.hardware.prover.memory, "memory-prover")
        self.v0_memory = self._build_memory("v0.memory", config.hardware.v0.memory, "memory-v0")
        self.prover_measurement = self._build_measurement(
            "prover.measurement", config.hardware.prover.measurement, "measurement-prover"
        )
        self.v0_measurement = self._build_measurement(
            "v0.measurement", config.hardware.v0.measurement, "measurement-v0"
        )
        self.qnd = self._build_qnd()
        self.clocks = {
            node: LocalClock(
                ClockCapabilities(0, 0, 0.0, 0.0, 1),
                random_streams.generator(f"clock-{node}"),
            )
            for node in ("v0", "v1", "prover", "controller")
        }
        self.classical_channel = AttackableClassicalChannel(scheduler, attacks, self._deliver_classical)

        bus.subscribe(self.EVENT_ROUND_START, self._on_round_start)
        bus.subscribe(self.EVENT_CHALLENGE_SEND, self._on_challenge_send)
        bus.subscribe(self.EVENT_QUANTUM_ARRIVAL, self._on_quantum_arrival)
        bus.subscribe(self.EVENT_INTERCEPT_COMPLETE, self._on_intercept_complete)
        bus.subscribe(self.EVENT_REPLACEMENT_SEND, self._on_replacement_send)
        bus.subscribe(self.EVENT_BASIS_SEND, self._on_basis_send)
        bus.subscribe(self.EVENT_ROUND_TIMEOUT, self._on_round_timeout)
        bus.subscribe(self.EVENT_FINAL_TIMEOUT, self._on_final_timeout)
        bus.subscribe(AttackableClassicalChannel.EVENT_ARRIVAL, self._on_classical_arrival)

    def _build_source(self) -> EprSource:
        cfg = self.config.hardware.v0.epr_source
        if cfg is None:
            raise ValueError("v0 EPR source is required")
        return EprSource(
            "v0.epr-source",
            EprSourceCapabilities(
                cfg.generation_latency,
                cfg.success_probability,
                cfg.pair_fidelity,
                cfg.repetition_rate_hz,
            ),
            self.scheduler,
            self.bus,
            self.quantum,
            self.random_streams.generator("source-v0"),
        )

    def _build_memory(self, memory_id: str, cfg, stream: str) -> TimedQuantumMemory:
        return TimedQuantumMemory(
            memory_id,
            MemoryCapabilities(
                cfg.load_latency,
                cfg.retrieve_latency,
                cfg.load_efficiency,
                cfg.retrieve_efficiency,
                cfg.t1,
                cfg.t2,
                cfg.maximum_hold,
            ),
            self.scheduler,
            self.bus,
            self.quantum,
            self.random_streams.generator(stream),
        )

    def _build_measurement(self, device_id: str, cfg, stream: str) -> TimedMeasurementDevice:
        return TimedMeasurementDevice(
            device_id,
            MeasurementCapabilities(
                cfg.basis_switch_latency,
                cfg.measurement_latency,
                cfg.measurement_fidelity,
                cfg.dead_time,
            ),
            self.scheduler,
            self.bus,
            self.quantum,
            self.random_streams.generator(stream),
        )

    def _build_qnd(self) -> QndDetector:
        cfg = self.config.hardware.prover.qnd
        return QndDetector(
            "prover.qnd",
            QndCapabilities(
                cfg.operation_latency,
                cfg.efficiency,
                cfg.dark_count_rate_hz,
                cfg.state_survival_probability,
                cfg.disturbance_probability,
                cfg.dead_time,
                cfg.gate_width,
            ),
            self.scheduler,
            self.bus,
            self.quantum,
            self.random_streams.generator("qnd-prover"),
        )

    def schedule(self) -> None:
        """Schedule every round start and timeout."""
        period = estimate_round_period_ps(self.config)
        for index in range(self.config.simulation.rounds):
            round_id = f"round-{index:06d}"
            start = int(self.config.protocol.initial_start) + index * period
            self.scheduler.schedule_at(
                start,
                EventPhase.CONTROL,
                DomainEvent(stable_id("round-start", self.session_id, index), self.EVENT_ROUND_START, {"round_id": round_id, "index": index}),
            )

    def session_result(self) -> SessionResult:
        ordered = tuple(sorted(self.results, key=lambda result: result.round_index))
        thresholds = AcceptanceThresholds(
            self.config.protocol.minimum_committed_rounds,
            self.config.protocol.maximum_qber,
            self.config.protocol.maximum_timing_violations,
            int(self.config.controller.clock_uncertainty),
        )
        return aggregate_session(self.session_id, ordered, thresholds)

    def _plan(self, round_id: str, index: int) -> RoundPlan:
        period = estimate_round_period_ps(self.config)
        round_start = int(self.config.protocol.initial_start) + index * period
        q_delay = propagation_delay_ps(
            self.positions["v0"], self.positions["prover"], self.config.geometry.propagation_speed_quantum_m_s
        )
        c_v0_p = self._classical_delay("v0", "prover")
        c_v1_p = self._classical_delay("v1", "prover")
        planning_lead = int(self.config.protocol.challenge_to_basis_delay) + max(c_v0_p, c_v1_p) + 1_000_000
        challenge_send = (
            round_start
            + planning_lead
            + int(self.config.hardware.v0.epr_source.generation_latency)
        )
        basis_arrival = challenge_send + q_delay + int(self.config.protocol.challenge_to_basis_delay)
        x_send = basis_arrival - c_v0_p
        y_send = basis_arrival - c_v1_p
        commitment_generated = (
            challenge_send
            + q_delay
            + int(self.config.hardware.prover.qnd.operation_latency)
            + int(self.config.hardware.prover.memory.load_latency)
        )
        answer_generated = (
            basis_arrival
            + int(self.config.hardware.prover.memory.retrieve_latency)
            + int(self.config.hardware.prover.measurement.basis_switch_latency)
            + int(self.config.hardware.prover.measurement.measurement_latency)
        )
        commitment_deadlines = {
            verifier: commitment_generated
            + self._classical_delay("prover", verifier)
            + int(self.config.protocol.response_slack)
            for verifier in ("v0", "v1")
        }
        answer_deadlines = {
            verifier: answer_generated
            + self._classical_delay("prover", verifier)
            + int(self.config.protocol.response_slack)
            for verifier in ("v0", "v1")
        }
        return RoundPlan(
            self.session_id,
            round_id,
            index,
            stable_id("nonce", self.session_id, round_id, self.config.simulation.seed),
            1,
            challenge_send,
            x_send,
            y_send,
            commitment_deadlines,
            answer_deadlines,
            self.positions["prover"],
            self.config.protocol.maximum_authenticated_radius_m,
        )

    def _on_round_start(self, event: DomainEvent) -> None:
        round_id = str(event.payload["round_id"])
        index = int(event.payload["index"])
        original = self._plan(round_id, index)
        context = self._attack_context(round_id)
        physical = self.attacks.alter_plan(original, context)
        if not isinstance(physical, RoundPlan):
            raise TypeError("plan attack returned wrong type")
        rng = self.random_streams.generator(f"round/{index}")
        runtime = _RoundRuntime(original, physical, rng, int(rng.integers(0, 2)), int(rng.integers(0, 2)))
        self.rounds[round_id] = runtime
        self._trace(round_id, "controller", "controller", "round_start", EventPhase.CONTROL, payload={"x": runtime.x, "y": runtime.y})

        policy_reasons = list(self.preflight_reason_codes)
        if self.config.controller.policy == "security_aware":
            controller_plan = physical if not physical.controller_expected_original else original
            schedule_decision = SchedulePolicy(
                ScheduleBounds(
                    minimum_delta_ps=0,
                    maximum_delta_ps=(
                        int(self.config.protocol.challenge_to_basis_delay)
                        + int(self.config.controller.clock_uncertainty)
                    ),
                    maximum_basis_skew_ps=int(self.config.controller.maximum_basis_skew),
                )
            ).validate(controller_plan)
            policy_reasons.extend(schedule_decision.reason_codes)
        if policy_reasons:
            runtime.completed = True
            self.results.append(
                RoundResult(
                    self.session_id, round_id, index, False, False, "not_executed",
                    None, None, None, None, None, None, None, None, None, None,
                    False, tuple(dict.fromkeys(policy_reasons)),
                    tuple(dict.fromkeys((*physical.physical_attack_ids, *self.attacks.attack_ids))),
                    self.positions["prover"].x_m,
                )
            )
            self._trace(
                round_id, "controller", "controller", "round_rejected_preflight",
                EventPhase.CONTROL, payload={"reasons": policy_reasons}
            )
            return

        q_delay = propagation_delay_ps(
            self.positions["v0"], self.positions["prover"], self.config.geometry.propagation_speed_quantum_m_s
        )
        expected_arrival = original.challenge_send_ps + q_delay
        gate_open = max(int(self.scheduler.now_ps()), expected_arrival - int(self.config.hardware.prover.qnd.gate_width) // 2)
        self.qnd.open_gate(
            round_id,
            gate_open,
            lambda result, rid=round_id: self._on_qnd_result(rid, result),
        )
        self.source.generate(
            f"{round_id}:pair",
            lambda pair, rid=round_id: self._on_pair_ready(rid, pair),
        )
        for input_name, when in (("x", physical.x_send_ps), ("y", physical.y_send_ps)):
            self.scheduler.schedule_at(
                when,
                EventPhase.PROTOCOL,
                DomainEvent(stable_id("basis-send", round_id, input_name, when), self.EVENT_BASIS_SEND, {"round_id": round_id, "input": input_name}),
            )
        timeout = max(original.answer_deadline_by_verifier.values()) + max(
            self._classical_delay("v0", "controller"), self._classical_delay("v1", "controller")
        ) + int(self.config.protocol.response_slack)
        self.scheduler.schedule_at(
            timeout,
            EventPhase.TIMEOUT,
            DomainEvent(stable_id("round-timeout", round_id), self.EVENT_ROUND_TIMEOUT, {"round_id": round_id}),
        )

    def _on_pair_ready(self, round_id: str, pair: QuantumPairHandle | None) -> None:
        runtime = self.rounds[round_id]
        if pair is None:
            self._trace(round_id, "v0", "v0.epr-source", "epr_generation_failed", EventPhase.DEVICE_COMPLETION)
            return
        runtime.pair = pair
        runtime.challenge = pair.second
        self._trace(round_id, "v0", "v0.epr-source", "epr_pair_ready", EventPhase.DEVICE_COMPLETION, quantum_object_id=pair.second.qubit_id)
        self.v0_memory.load(pair.first, lambda success, rid=round_id: self._on_v0_memory_loaded(rid, success))
        when = max(int(self.scheduler.now_ps()), runtime.physical_plan.challenge_send_ps)
        self.scheduler.schedule_at(
            when,
            EventPhase.PROTOCOL,
            DomainEvent(stable_id("challenge-send", round_id, when), self.EVENT_CHALLENGE_SEND, {"round_id": round_id}),
        )

    def _on_v0_memory_loaded(self, round_id: str, success: bool) -> None:
        runtime = self.rounds[round_id]
        runtime.v0_memory_ready = success
        self._trace(round_id, "v0", "v0.memory", "memory_load_complete", EventPhase.DEVICE_COMPLETION, payload={"success": success})
        self._try_measure(round_id)

    def _on_challenge_send(self, event: DomainEvent) -> None:
        round_id = str(event.payload["round_id"])
        runtime = self.rounds[round_id]
        if runtime.challenge is None:
            return
        link_length = self.quantum_link.length_m or distance(self.positions["v0"], self.positions["prover"])
        delay = int(math.ceil(link_length / self.config.geometry.propagation_speed_quantum_m_s * 1e12))
        survival = 10 ** (-self.quantum_link.attenuation_db_per_m * link_length / 10.0)
        tx = QuantumTransmission(
            stable_id("qtx", round_id, "challenge"),
            self.quantum_link.id,
            "v0",
            "prover",
            runtime.challenge,
            int(self.scheduler.now_ps()),
            delay,
            survival,
        )
        decision = self.attacks.decide_quantum_send(tx, self._attack_context(round_id))
        tx = decision.transmission
        self._trace(round_id, "v0", self.quantum_link.id, "quantum_send", EventPhase.PROTOCOL, transmission_id=tx.transmission_id, quantum_object_id=tx.qubit.qubit_id, attack_ids=tx.attack_ids)
        if not decision.allow or tx.dropped or runtime.rng.random() >= tx.survival_probability:
            self._trace(round_id, "v0", self.quantum_link.id, "quantum_drop", EventPhase.PROTOCOL, transmission_id=tx.transmission_id, attack_ids=tx.attack_ids)
            return
        if self.intercept_attack is not None:
            self._schedule_intercept(round_id, tx)
            return
        self.scheduler.schedule_at(
            tx.arrival_time_ps,
            EventPhase.PHYSICAL_ARRIVAL,
            DomainEvent(stable_id("q-arrival", tx.transmission_id), self.EVENT_QUANTUM_ARRIVAL, {"round_id": round_id, "qubit": tx.qubit, "attack_ids": tx.attack_ids}),
        )

    def _schedule_intercept(self, round_id: str, tx: QuantumTransmission) -> None:
        attack = self.intercept_attack
        assert attack is not None
        interceptor = Position(attack.position_m, 0.0)
        delay = propagation_delay_ps(self.positions["v0"], interceptor, self.config.geometry.propagation_speed_quantum_m_s)
        when = tx.send_time_ps + delay + attack.processing_latency_ps
        self.scheduler.schedule_at(
            when,
            EventPhase.DEVICE_COMPLETION,
            DomainEvent(stable_id("intercept", round_id, when), self.EVENT_INTERCEPT_COMPLETE, {"round_id": round_id, "qubit": tx.qubit}),
        )
        self._trace(round_id, "attacker", attack.attack_id, "quantum_intercept_scheduled", EventPhase.PROTOCOL, attack_ids=(attack.attack_id,))

    def _on_intercept_complete(self, event: DomainEvent) -> None:
        attack = self.intercept_attack
        assert attack is not None
        round_id = str(event.payload["round_id"])
        runtime = self.rounds[round_id]
        original: QuantumHandle = event.payload["qubit"]
        if attack.basis_strategy == "random":
            basis = int(runtime.rng.integers(0, 2))
        elif attack.basis_strategy == "z_only":
            basis = 0
        else:
            basis = 1
        bit = self.quantum.measure_bb84(original, basis, runtime.rng)
        replacement = self.quantum.prepare_bb84(
            f"{round_id}:replacement-qubit",
            f"{round_id}:replacement-state",
            basis,
            bit,
        )
        if attack.replacement_source_fidelity < 1:
            self.quantum.apply_kraus(replacement, depolarizing(1 - attack.replacement_source_fidelity))
        when = int(self.scheduler.now_ps()) + attack.preparation_latency_ps
        self.scheduler.schedule_at(
            when,
            EventPhase.PROTOCOL,
            DomainEvent(stable_id("replacement-send", round_id, when), self.EVENT_REPLACEMENT_SEND, {"round_id": round_id, "qubit": replacement, "basis": basis, "bit": bit}),
        )
        self._trace(round_id, "attacker", attack.attack_id, "intercept_measure_complete", EventPhase.DEVICE_COMPLETION, quantum_object_id=original.qubit_id, attack_ids=(attack.attack_id,), payload={"basis": basis, "bit": bit})

    def _on_replacement_send(self, event: DomainEvent) -> None:
        attack = self.intercept_attack
        assert attack is not None
        round_id = str(event.payload["round_id"])
        replacement: QuantumHandle = event.payload["qubit"]
        interceptor = Position(attack.position_m, 0.0)
        delay = propagation_delay_ps(interceptor, self.positions["prover"], self.config.geometry.propagation_speed_quantum_m_s)
        when = int(self.scheduler.now_ps()) + delay
        self.scheduler.schedule_at(
            when,
            EventPhase.PHYSICAL_ARRIVAL,
            DomainEvent(stable_id("replacement-arrival", round_id, when), self.EVENT_QUANTUM_ARRIVAL, {"round_id": round_id, "qubit": replacement, "attack_ids": (attack.attack_id,)}),
        )

    def _on_quantum_arrival(self, event: DomainEvent) -> None:
        round_id = str(event.payload["round_id"])
        qubit: QuantumHandle = event.payload["qubit"]
        if self.quantum_link.polarization_fidelity < 1:
            self.quantum.apply_kraus(qubit, depolarizing(1 - self.quantum_link.polarization_fidelity))
        self._trace(round_id, "prover", "prover.qnd", "quantum_arrival", EventPhase.PHYSICAL_ARRIVAL, quantum_object_id=qubit.qubit_id, attack_ids=tuple(event.payload.get("attack_ids", ())))
        self.qnd.photon_arrival(round_id, qubit)

    def _on_qnd_result(self, round_id: str, result: QndResult) -> None:
        runtime = self.rounds[round_id]
        runtime.qnd_outcome = result.outcome
        self._trace(round_id, "prover", "prover.qnd", "qnd_result", EventPhase.DEVICE_COMPLETION, payload={"outcome": result.outcome.value})
        if result.outcome is QndOutcome.VALID_DETECTION and result.qubit is not None:
            self.prover_memory.load(result.qubit, lambda success, rid=round_id: self._on_prover_memory_loaded(rid, success))
        elif result.outcome is QndOutcome.DARK_COUNT:
            runtime.committed = True
            runtime.valid_state_commitment = False
            runtime.commitment_generated_ps = int(self.scheduler.now_ps())
            self._broadcast_commitment(round_id, 1)
        else:
            runtime.committed = False
            runtime.commitment_generated_ps = int(self.scheduler.now_ps())
            self._broadcast_commitment(round_id, 0)

    def _on_prover_memory_loaded(self, round_id: str, success: bool) -> None:
        runtime = self.rounds[round_id]
        runtime.committed = success
        runtime.valid_state_commitment = success
        runtime.commitment_generated_ps = int(self.scheduler.now_ps())
        self._trace(round_id, "prover", "prover.memory", "memory_load_complete", EventPhase.DEVICE_COMPLETION, payload={"success": success})
        self._broadcast_commitment(round_id, 1 if success else 0)
        self._try_measure(round_id)

    def _broadcast_commitment(self, round_id: str, commitment: int) -> None:
        runtime = self.rounds[round_id]
        for verifier in ("v0", "v1"):
            message = ProtocolMessage(
                "1.0",
                MessageType.COMMITMENT,
                self.session_id,
                round_id,
                "prover",
                verifier,
                runtime.original_plan.nonce,
                runtime.original_plan.telemetry_epoch,
                {"commitment": commitment},
            )
            self._send_classical("prover", verifier, message, round_id)
        self._trace(round_id, "prover", "prover", "commitment_generated", EventPhase.PROTOCOL, local_time_ps=self.clocks["prover"].observe(int(self.scheduler.now_ps())), payload={"commitment": commitment})

    def _on_basis_send(self, event: DomainEvent) -> None:
        round_id = str(event.payload["round_id"])
        name = str(event.payload["input"])
        runtime = self.rounds[round_id]
        source = "v0" if name == "x" else "v1"
        message_type = MessageType.BASIS_INPUT_X if name == "x" else MessageType.BASIS_INPUT_Y
        bit = runtime.x if name == "x" else runtime.y
        message = ProtocolMessage(
            "1.0",
            message_type,
            self.session_id,
            round_id,
            source,
            "prover",
            runtime.original_plan.nonce,
            runtime.original_plan.telemetry_epoch,
            {"bit": bit},
        )
        self._send_classical(source, "prover", message, round_id)
        self._trace(round_id, source, source, f"basis_{name}_sent", EventPhase.PROTOCOL, payload={"bit": bit})

    def _send_classical(self, source: str, destination: str, message: ProtocolMessage, round_id: str) -> None:
        link = self.classical_links[(source, destination)]
        tx = ClassicalTransmission(
            stable_id("ctx", round_id, source, destination, message.message_type.value, int(self.scheduler.now_ps())),
            link.id,
            source,
            destination,
            message.message_type.value,
            message,
            int(self.scheduler.now_ps()),
            self._classical_delay(source, destination),
            int(link.sender_delay),
        )
        outputs = self.classical_channel.send(tx, self._attack_context(round_id))
        for output in outputs:
            event_type = "classical_drop" if output.dropped else "classical_send"
            self._trace(round_id, source, output.link_id, event_type, EventPhase.PROTOCOL, transmission_id=output.transmission_id, attack_ids=output.attack_ids, payload={"message_type": output.message_type, "destination": destination})

    def _on_classical_arrival(self, event: DomainEvent) -> None:
        tx: ClassicalTransmission = event.payload
        message: ProtocolMessage = tx.payload
        round_id = message.round_id
        if round_id is None or round_id not in self.rounds:
            return
        self._trace(round_id, tx.destination, tx.link_id, "classical_arrival", EventPhase.PHYSICAL_ARRIVAL, transmission_id=tx.transmission_id, attack_ids=tx.attack_ids, payload={"message_type": tx.message_type, "source": tx.source})
        runtime = self.rounds[round_id]
        if tx.destination == "prover":
            if message.message_type is MessageType.BASIS_INPUT_X:
                runtime.x_arrival_ps = int(self.scheduler.now_ps())
            elif message.message_type is MessageType.BASIS_INPUT_Y:
                runtime.y_arrival_ps = int(self.scheduler.now_ps())
            self._try_measure(round_id)
            return
        if tx.destination in {"v0", "v1"}:
            observation = runtime.observations[tx.destination]
            now = int(self.scheduler.now_ps())
            local = self.clocks[tx.destination].observe(now)
            if message.message_type is MessageType.COMMITMENT:
                observation.commitment = int(message.payload["commitment"])
                observation.commitment_physical_ps = now
                observation.commitment_local_ps = local
            elif message.message_type is MessageType.ANSWER:
                observation.answer = int(message.payload["answer"])
                observation.answer_physical_ps = now
                observation.answer_local_ps = local
            self._maybe_send_report(round_id, tx.destination)
            return
        if tx.destination == "controller" and message.message_type is MessageType.VERIFIER_REPORT:
            report: VerifierReport = message.payload
            runtime.reports[report.verifier_id] = report
            if len(runtime.reports) == 2:
                self._finalize_round(round_id)

    def _try_measure(self, round_id: str) -> None:
        runtime = self.rounds[round_id]
        if runtime.measurement_started or not runtime.valid_state_commitment:
            return
        if runtime.x_arrival_ps is None or runtime.y_arrival_ps is None:
            return
        if self.prover_memory.state is not MemoryState.STORED or self.v0_memory.state is not MemoryState.STORED:
            return
        runtime.measurement_started = True
        basis = xor_basis(runtime.x, runtime.y)
        self.prover_memory.retrieve(
            lambda qubit, dwell, rid=round_id, b=basis: self._on_prover_retrieved(rid, qubit, dwell, b)
        )
        self.v0_memory.retrieve(
            lambda qubit, dwell, rid=round_id, b=basis: self._on_v0_retrieved(rid, qubit, dwell, b)
        )

    def _on_prover_retrieved(self, round_id: str, qubit: QuantumHandle | None, dwell: int, basis: int) -> None:
        runtime = self.rounds[round_id]
        runtime.memory_dwell_ps = dwell
        if qubit is None:
            return
        self.prover_measurement.measure(
            qubit,
            basis,
            lambda result, rid=round_id: self._on_prover_measurement(rid, result),
        )

    def _on_v0_retrieved(self, round_id: str, qubit: QuantumHandle | None, dwell: int, basis: int) -> None:
        if qubit is None:
            return
        self.v0_measurement.measure(
            qubit,
            basis,
            lambda result, rid=round_id: self._on_v0_measurement(rid, result),
        )

    def _on_prover_measurement(self, round_id: str, result: int) -> None:
        runtime = self.rounds[round_id]
        runtime.prover_measurement = result
        for verifier in ("v0", "v1"):
            message = ProtocolMessage(
                "1.0",
                MessageType.ANSWER,
                self.session_id,
                round_id,
                "prover",
                verifier,
                runtime.original_plan.nonce,
                runtime.original_plan.telemetry_epoch,
                {"answer": result},
            )
            self._send_classical("prover", verifier, message, round_id)
        self._trace(round_id, "prover", "prover.measurement", "prover_measurement_complete", EventPhase.DEVICE_COMPLETION, payload={"result": result})

    def _on_v0_measurement(self, round_id: str, result: int) -> None:
        self.rounds[round_id].verifier_measurement = result
        self._trace(round_id, "v0", "v0.measurement", "verifier_measurement_complete", EventPhase.DEVICE_COMPLETION, payload={"result": result})
        self._maybe_send_report(round_id, "v0")

    def _maybe_send_report(self, round_id: str, verifier: str, *, force: bool = False) -> None:
        runtime = self.rounds[round_id]
        observation = runtime.observations[verifier]
        if observation.report_sent:
            return
        ready = observation.commitment is not None and observation.answer is not None
        if verifier == "v0":
            ready = ready and runtime.verifier_measurement is not None
        if not ready and not force:
            return
        plan = runtime.original_plan
        report = VerifierReport(
            self.session_id,
            round_id,
            verifier,
            plan.nonce,
            plan.telemetry_epoch,
            observation.commitment,
            observation.answer,
            runtime.verifier_measurement if verifier == "v0" else None,
            observation.commitment_physical_ps,
            observation.commitment_local_ps,
            observation.commitment_local_ps,
            observation.answer_physical_ps,
            observation.answer_local_ps,
            observation.answer_local_ps,
            plan.commitment_deadline_by_verifier[verifier],
            plan.answer_deadline_by_verifier[verifier],
        )
        attacked = self.attacks.alter_report(report, self._attack_context(round_id))
        if not isinstance(attacked, VerifierReport):
            raise TypeError("report attack returned wrong type")
        observation.report_sent = True
        message = ProtocolMessage(
            "1.0",
            MessageType.VERIFIER_REPORT,
            self.session_id,
            round_id,
            verifier,
            "controller",
            plan.nonce,
            plan.telemetry_epoch,
            attacked,
        )
        self._send_classical(verifier, "controller", message, round_id)

    def _on_round_timeout(self, event: DomainEvent) -> None:
        round_id = str(event.payload["round_id"])
        runtime = self.rounds[round_id]
        if runtime.completed:
            return
        self._maybe_send_report(round_id, "v0", force=True)
        self._maybe_send_report(round_id, "v1", force=True)
        # Give forced reports one final propagation window before failing closed.
        final_delay = max(
            self._classical_delay("v0", "controller"),
            self._classical_delay("v1", "controller"),
        ) + 1
        self.scheduler.schedule_after(
            final_delay,
            EventPhase.TIMEOUT,
            DomainEvent(
                stable_id("round-final-timeout", round_id),
                self.EVENT_FINAL_TIMEOUT,
                {"round_id": round_id},
            ),
        )

    def _on_final_timeout(self, event: DomainEvent) -> None:
        round_id = str(event.payload["round_id"])
        if not self.rounds[round_id].completed:
            self._finalize_round(round_id)

    def _finalize_round(self, round_id: str) -> None:
        runtime = self.rounds[round_id]
        if runtime.completed:
            return
        reports = tuple(runtime.reports.values())
        if self.config.controller.policy == "security_aware":
            decision = SecurityAwareRoundAcceptance(int(self.config.controller.clock_uncertainty)).decide(
                runtime.original_plan, reports
            )
        else:
            decision = BaselineRoundAcceptance().decide(runtime.original_plan, reports)
        basis_available = (
            max(runtime.x_arrival_ps, runtime.y_arrival_ps)
            if runtime.x_arrival_ps is not None and runtime.y_arrival_ps is not None
            else None
        )
        expected_basis = max(
            runtime.original_plan.x_send_ps + self._classical_delay("v0", "prover"),
            runtime.original_plan.y_send_ps + self._classical_delay("v1", "prover"),
        )
        inferred_commitment_generation = [
            report.commitment_reported_ps
            - self._classical_delay("prover", report.verifier_id)
            for report in reports
            if report.commitment_reported_ps is not None
        ]
        # The controller uses the latest inferred generation time as the conservative
        # commitment timestamp. Report timestamps are verifier-local observations of
        # arrival and must first be translated back to the prover using the configured
        # propagation model.
        controller_margin = (
            expected_basis - max(inferred_commitment_generation)
            if inferred_commitment_generation
            else None
        )
        reports_by_id = {report.verifier_id: report for report in reports}
        v0 = reports_by_id.get("v0")
        v1 = reports_by_id.get("v1")
        result = RoundResult(
            self.session_id,
            round_id,
            runtime.original_plan.round_index,
            runtime.committed,
            runtime.valid_state_commitment,
            runtime.qnd_outcome.value if runtime.qnd_outcome is not None else "none",
            runtime.prover_measurement,
            runtime.verifier_measurement,
            (
                runtime.prover_measurement == runtime.verifier_measurement
                if runtime.prover_measurement is not None and runtime.verifier_measurement is not None
                else None
            ),
            runtime.memory_dwell_ps,
            commitment_margin_ps(basis_available, runtime.commitment_generated_ps),
            controller_margin,
            response_margin_ps(runtime.original_plan.answer_deadline_by_verifier["v0"], v0.answer_physical_ps if v0 else None),
            response_margin_ps(runtime.original_plan.answer_deadline_by_verifier["v0"], v0.answer_reported_ps if v0 else None),
            response_margin_ps(runtime.original_plan.answer_deadline_by_verifier["v1"], v1.answer_physical_ps if v1 else None),
            response_margin_ps(runtime.original_plan.answer_deadline_by_verifier["v1"], v1.answer_reported_ps if v1 else None),
            decision.accepted,
            decision.reason_codes,
            tuple(dict.fromkeys((*runtime.physical_plan.physical_attack_ids, *self.attacks.attack_ids))),
            self.positions["prover"].x_m,
        )
        attacked_result = self.attacks.alter_result(result, self._attack_context(round_id))
        if not isinstance(attacked_result, RoundResult):
            raise TypeError("result attack returned wrong type")
        runtime.completed = True
        self.results.append(attacked_result)
        self._trace(round_id, "controller", "controller", "round_complete", EventPhase.CONTROL, payload={"accepted": attacked_result.accepted, "reasons": list(attacked_result.reason_codes)})
        if (
            self.prover_memory.qubit is not None
            and self.prover_memory.qubit.qubit_id.startswith(round_id)
            and self.prover_memory.state in {MemoryState.STORED, MemoryState.EXPIRED, MemoryState.FAILED}
        ):
            self.prover_memory.discard()
        if (
            self.v0_memory.qubit is not None
            and self.v0_memory.qubit.qubit_id.startswith(round_id)
            and self.v0_memory.state in {MemoryState.STORED, MemoryState.EXPIRED, MemoryState.FAILED}
        ):
            self.v0_memory.discard()

    def _deliver_classical(self, transmission: ClassicalTransmission) -> None:
        # Delivery is handled by the bus subscriber; the callback is kept for the channel port.
        return None

    def _classical_delay(self, source: str, destination: str) -> int:
        link = self.classical_links[(source, destination)]
        if link.length_m is not None:
            length = link.length_m
        else:
            length = distance(self.positions[source], self.positions[destination])
        return int(math.ceil(length / self.config.geometry.propagation_speed_classical_m_s * 1e12)) + int(link.sender_delay)

    def _attack_context(self, round_id: str | None) -> AttackContext:
        suffix = round_id or "session"
        return AttackContext(
            int(self.scheduler.now_ps()),
            self.session_id,
            round_id,
            self.random_streams.generator(f"attacks/{suffix}"),
        )

    def _trace(
        self,
        round_id: str | None,
        node_id: str | None,
        component_id: str | None,
        event_type: str,
        phase: EventPhase,
        *,
        local_time_ps: int | None = None,
        reported_time_ps: int | None = None,
        transmission_id: str | None = None,
        quantum_object_id: str | None = None,
        attack_ids: tuple[str, ...] = (),
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._trace_sequence += 1
        self.trace_sink.append(
            TraceEvent(
                "1.0",
                self.run_id,
                self.session_id,
                round_id,
                f"trace-{self._trace_sequence:012d}",
                int(self.scheduler.now_ps()),
                phase.name,
                node_id,
                component_id,
                event_type,
                local_time_ps,
                reported_time_ps,
                transmission_id,
                quantum_object_id,
                attack_ids,
                payload or {},
            )
        )
