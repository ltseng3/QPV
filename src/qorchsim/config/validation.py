"""Additional execution-bound semantic validation."""

from __future__ import annotations

from qorchsim.config.models import QOrchSimConfig
from qorchsim.errors import ConfigurationError
from qorchsim.network.geometry import Position, propagation_delay_ps


def estimate_round_period_ps(config: QOrchSimConfig) -> int:
    nodes = {key: Position(value.x_m, value.y_m) for key, value in config.geometry.nodes.items()}
    quantum_delay = propagation_delay_ps(
        nodes["v0"], nodes["prover"], config.geometry.propagation_speed_quantum_m_s
    )
    classical = max(
        propagation_delay_ps(nodes["prover"], nodes["v0"], config.geometry.propagation_speed_classical_m_s),
        propagation_delay_ps(nodes["prover"], nodes["v1"], config.geometry.propagation_speed_classical_m_s),
    )
    # A round with no valid commitment is finalized only after each verifier has had a
    # chance to emit a forced report and that report can reach the controller. Include
    # this path in the period so one-slot memories are released before the next round.
    controller_report = max(
        propagation_delay_ps(nodes["v0"], nodes["controller"], config.geometry.propagation_speed_classical_m_s),
        propagation_delay_ps(nodes["v1"], nodes["controller"], config.geometry.propagation_speed_classical_m_s),
    )
    hardware = config.hardware
    planning_lead = int(config.protocol.challenge_to_basis_delay) + max(
        propagation_delay_ps(nodes["v0"], nodes["prover"], config.geometry.propagation_speed_classical_m_s),
        propagation_delay_ps(nodes["v1"], nodes["prover"], config.geometry.propagation_speed_classical_m_s),
    ) + 1_000_000
    return int(
        planning_lead
        + hardware.v0.epr_source.generation_latency
        + quantum_delay
        + config.protocol.challenge_to_basis_delay
        + hardware.prover.qnd.operation_latency
        + hardware.prover.memory.load_latency
        + hardware.prover.memory.retrieve_latency
        + hardware.prover.measurement.basis_switch_latency
        + hardware.prover.measurement.measurement_latency
        + classical
        + 2 * int(config.protocol.response_slack)
        + 2 * controller_report
        + 1_000_001
    )


def validate_execution_horizon(config: QOrchSimConfig) -> None:
    latest = int(config.protocol.initial_start) + config.simulation.rounds * estimate_round_period_ps(config)
    latest += int(config.simulation.cleanup_margin)
    if int(config.simulation.stop_time) <= latest:
        raise ConfigurationError(
            f"stop_time={config.simulation.stop_time} ps is too short; estimated minimum is {latest + 1} ps"
        )
