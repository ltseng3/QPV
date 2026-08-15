"""Deterministic single-run experiment service."""

from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qorchsim.adapters.sequence.version import check_sequence_version
from qorchsim.attacks.base import AttackContext
from qorchsim.attacks.intercept_resend import InterceptResendAttack
from qorchsim.attacks.pipeline import AttackPipeline
from qorchsim.attacks.schedule_skew import ScheduleSkewAttack
from qorchsim.attacks.selective_jamming import SelectiveJammingAttack
from qorchsim.attacks.telemetry_poisoning import TelemetryPoisoningAttack
from qorchsim.attacks.timestamp_forgery import TimestampForgeryAttack
from qorchsim.cloudsim.resources import DeviceResource, LinkResource, NodeResource, ResourceSnapshot
from qorchsim.cloudsim.static_scheduler import StaticQpvScheduler
from qorchsim.cloudsim.workloads import QpvWorkload
from qorchsim.config.models import (
    InterceptResendAttackConfig,
    QOrchSimConfig,
    ScheduleSkewAttackConfig,
    SelectiveJammingAttackConfig,
    TelemetryPoisoningAttackConfig,
    TimestampForgeryAttackConfig,
)
from qorchsim.config.normalization import configuration_hash, normalized_dict
from qorchsim.config.validation import validate_execution_horizon
from qorchsim.core.event_bus import EventBus
from qorchsim.core.random_streams import RandomStreams
from qorchsim.core.scheduler import DeterministicScheduler
from qorchsim.metrics.records import round_record
from qorchsim.metrics.security import security_summary
from qorchsim.metrics.timing import timing_summary
from qorchsim.network.geometry import Position, distance
from qorchsim.qpv.execution import QpvExecutionModel
from qorchsim.qpv.session import QpvSessionRuntime
from qorchsim.quantum.operations import DensityMatrixQuantumOperations
from qorchsim.tracing.manifest import RunManifest
from qorchsim.tracing.ndjson import NdjsonTraceSink
from qorchsim.tracing.sink import NullTraceSink, TraceSink


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    run_id: str
    output_directory: Path
    summary: dict[str, Any]


def _attack_pipeline(config: QOrchSimConfig) -> AttackPipeline:
    attacks = []
    for item in config.attacks:
        if isinstance(item, ScheduleSkewAttackConfig):
            attacks.append(
                ScheduleSkewAttack(
                    item.id,
                    x_shift_ps=int(item.x_shift),
                    y_shift_ps=int(item.y_shift),
                    challenge_shift_ps=int(item.challenge_shift),
                    modify_controller_view=item.modify_controller_view,
                )
            )
        elif isinstance(item, TelemetryPoisoningAttackConfig):
            fields = {
                key: int(value) if isinstance(value, (int, float)) and key.endswith("_ps") else value
                for key, value in item.fields.items()
            }
            attacks.append(TelemetryPoisoningAttack(item.id, item.resource_id, fields))
        elif isinstance(item, TimestampForgeryAttackConfig):
            attacks.append(TimestampForgeryAttack(item.id, item.node_id, int(item.bias), item.fields))
        elif isinstance(item, SelectiveJammingAttackConfig):
            attacks.append(
                SelectiveJammingAttack(
                    item.id,
                    link_ids=item.link_ids,
                    message_types=item.message_types,
                    start_ps=int(item.start),
                    end_ps=int(item.end) if item.end is not None else None,
                    drop_probability=item.drop_probability,
                    added_delay_ps=int(item.added_delay),
                    quantum=item.quantum,
                )
            )
        elif isinstance(item, InterceptResendAttackConfig):
            attacks.append(
                InterceptResendAttack(
                    item.id,
                    position_m=item.position_m,
                    basis_strategy=item.basis_strategy,
                    processing_latency_ps=int(item.processing_latency),
                    preparation_latency_ps=int(item.preparation_latency),
                    replacement_source_fidelity=item.replacement_source_fidelity,
                )
            )
    return AttackPipeline(attacks)


def _resource_snapshot(config: QOrchSimConfig) -> ResourceSnapshot:
    nodes = tuple(
        NodeResource(node_id, (position.x_m, position.y_m))
        for node_id, position in sorted(config.geometry.nodes.items())
    )
    devices = (
        DeviceResource(
            "v0.memory",
            "v0",
            "quantum_memory",
            {
                "t1_ps": config.hardware.v0.memory.t1,
                "t2_ps": config.hardware.v0.memory.t2,
                "maximum_hold_ps": config.hardware.v0.memory.maximum_hold,
            },
            {
                "t1_ps": config.hardware.v0.memory.t1,
                "t2_ps": config.hardware.v0.memory.t2,
                "maximum_hold_ps": config.hardware.v0.memory.maximum_hold,
            },
        ),
        DeviceResource(
            "prover.memory",
            "prover",
            "quantum_memory",
            {
                "t1_ps": config.hardware.prover.memory.t1,
                "t2_ps": config.hardware.prover.memory.t2,
                "maximum_hold_ps": config.hardware.prover.memory.maximum_hold,
            },
            {
                "t1_ps": config.hardware.prover.memory.t1,
                "t2_ps": config.hardware.prover.memory.t2,
                "maximum_hold_ps": config.hardware.prover.memory.maximum_hold,
            },
        ),
    )
    positions = {
        node_id: Position(position.x_m, position.y_m)
        for node_id, position in config.geometry.nodes.items()
    }
    links = tuple(
        LinkResource(
            link.id,
            link.source,
            link.destination,
            "quantum",
            link.length_m or distance(positions[link.source], positions[link.destination]),
        )
        for link in config.links.quantum
    ) + tuple(
        LinkResource(
            link.id,
            link.source,
            link.destination,
            "classical",
            link.length_m or distance(positions[link.source], positions[link.destination]),
        )
        for link in config.links.classical
    )
    return ResourceSnapshot(0, nodes, devices, links, 1)


def _backend(config: QOrchSimConfig, warnings: list[str]):
    if config.execution.model == "sequence_qpv":
        _, sequence_warnings = check_sequence_version(
            allow_unsupported=config.execution.allow_unsupported_sequence_version
        )
        warnings.extend(sequence_warnings)
        from qorchsim.adapters.sequence.scenario_builder import build_sequence_backend

        return build_sequence_backend(int(config.simulation.stop_time))
    warnings.append("portable deterministic backend selected; SeQUeNCe adapter not active")
    bus = EventBus()
    scheduler = DeterministicScheduler(bus, int(config.simulation.stop_time))
    quantum = DensityMatrixQuantumOperations()
    return bus, scheduler, quantum


def run_experiment(
    config: QOrchSimConfig,
    *,
    output_directory: str | Path | None = None,
    seed_override: int | None = None,
) -> RunArtifacts:
    """Run one validated configuration and atomically persist outputs."""
    if seed_override is not None:
        config = config.model_copy(
            update={"simulation": config.simulation.model_copy(update={"seed": seed_override})}
        )
    validate_execution_horizon(config)
    config_hash = configuration_hash(config)
    run_id = f"run-{config_hash[:12]}-{config.simulation.seed}"
    target = Path(output_directory or config.output.directory)
    temporary = target.with_name(f".{target.name}.{run_id}.tmp")
    failed = target.with_name(f"{target.name}.{run_id}.failed")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    manifest = RunManifest.start(
        run_id,
        normalized_dict(config),
        config.simulation.seed,
        warnings,
    )
    trace_sink: TraceSink
    if config.output.write_event_ndjson and config.output.trace_level != "none":
        trace_sink = NdjsonTraceSink(temporary / "events.ndjson")
    else:
        trace_sink = NullTraceSink()
    try:
        bus, scheduler, quantum = _backend(config, warnings)
        streams = RandomStreams(config.simulation.seed)
        attacks = _attack_pipeline(config)
        truth = _resource_snapshot(config)
        attacked_resources = attacks.alter_inventory(
            truth,
            AttackContext(
                0,
                "session-0",
                None,
                streams.generator("attacks/session"),
            ),
        )
        workload = QpvWorkload(
            workload_id="workload-qpv-0",
            workload_type="commitment_qpv",
            arrival_time_ps=int(config.protocol.initial_start),
            deadline_ps=int(config.simulation.stop_time),
            priority=0,
            parameters={"participants": ("controller", "v0", "v1", "prover")},
            session_spec={"rounds": config.simulation.rounds},
        )
        scheduling = StaticQpvScheduler().schedule(workload, attacked_resources, 0)
        if not scheduling.accepted or scheduling.allocation is None:
            raise RuntimeError(f"workload rejected: {scheduling.reason_codes}")
        runtime = QpvSessionRuntime(
            run_id=run_id,
            session_id="session-0",
            config=config,
            scheduler=scheduler,
            bus=bus,
            quantum=quantum,
            attacks=attacks,
            resources=attacked_resources,
            random_streams=streams,
            trace_sink=trace_sink,
        )
        QpvExecutionModel(runtime).submit(workload, scheduling.allocation)
        scheduler.run()
        result = runtime.session_result()
        trace_sink.close()

        if config.output.write_round_csv:
            rows = [round_record(item) for item in result.rounds]
            if rows:
                with (temporary / "rounds.csv").open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
        summary = {
            "schema_version": "1.0",
            "run_id": run_id,
            "security": security_summary(result, config.protocol.maximum_authenticated_radius_m),
            "timing": timing_summary(result),
            "attack_ids": list(attacks.attack_ids),
            "backend": config.execution.model,
        }
        (temporary / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
        )
        manifest.finish(getattr(scheduler, "dispatched", 0))
        (temporary / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        if target.exists():
            shutil.rmtree(target)
        os.replace(temporary, target)
        return RunArtifacts(run_id, target, summary)
    except Exception as exc:
        try:
            trace_sink.close()
        except Exception:
            pass
        manifest.warnings.append(f"execution_failed:{type(exc).__name__}:{exc}")
        (temporary / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        (temporary / "exception.txt").write_text(
            f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
        )
        if failed.exists():
            shutil.rmtree(failed)
        os.replace(temporary, failed)
        raise
