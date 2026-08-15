# Configuration Reference

QOrchSim configurations are strict YAML documents validated by Pydantic. Unknown
fields are rejected, durations must carry a supported unit unless they are already
integer picoseconds, and semantic checks run before any simulation backend is
initialized.

## Top-level structure

```yaml
schema_version: "1.0"
simulation: {}
execution: {}
geometry: {}
hardware: {}
links: {}
protocol: {}
controller: {}
attacks: []
output: {}
```

## Duration syntax

The parser accepts non-negative values with the units `ps`, `ns`, `us`, `µs`, `ms`,
or `s`. Raw integers are interpreted as picoseconds. Signed values are accepted only
for attack fields where a negative offset is meaningful.

```yaml
operation_latency: 100 ns
challenge_to_basis_delay: 5 us
stop_time: 100 ms
x_shift: -2 us
```

## `simulation`

| Field | Meaning | Default/constraint |
|---|---|---|
| `seed` | Master seed for named deterministic random streams | `12345` |
| `stop_time` | Exclusive simulation horizon | positive duration |
| `rounds` | Number of QPV rounds | at least 1 |
| `quantum_formalism` | Quantum representation | `density_matrix` only in v1 |
| `cleanup_margin` | Extra horizon validation margin | `10 us` |

A SeQUeNCe event at exactly `stop_time` is not executed, so configuration validation
requires enough margin for the last response and cleanup events.

## `execution`

| Field | Meaning |
|---|---|
| `model` | `sequence_qpv` for the SeQUeNCe adapter or `portable_qpv` for deterministic portable validation |
| `parallel_processes` | Process count used by sweep execution |
| `allow_unsupported_sequence_version` | Permit a non-1.0.0 SeQUeNCe version with a manifest warning |

Publication-oriented runs should use `sequence_qpv`. The portable backend executes the
same protocol, attack, timing, and density-matrix contracts and is intended for rapid
testing and environments where SeQUeNCe is unavailable.

## `geometry`

```yaml
geometry:
  dimension: 1
  propagation_speed_quantum_m_s: 2.0e8
  propagation_speed_classical_m_s: 2.0e8
  nodes:
    controller: {x_m: 0, y_m: 0}
    v0: {x_m: -1000, y_m: 0}
    prover: {x_m: 0, y_m: 0}
    v1: {x_m: 1000, y_m: 0}
```

The required logical nodes are `controller`, `v0`, `v1`, and `prover`. Link lengths
are derived from Euclidean coordinates unless `length_m` is explicitly supplied on a
link.

## `hardware.v0`

`v0` owns an EPR source, retained memory, and measurement device.

### EPR source

| Field | Meaning |
|---|---|
| `generation_latency` | Time from request to pair availability |
| `success_probability` | Pair generation success probability |
| `pair_fidelity` | Initial fidelity to the Bell state; range `[0.25, 1]` |
| `repetition_rate_hz` | Maximum generation rate |

### Quantum memory

| Field | Meaning |
|---|---|
| `load_latency` | Time before a state becomes resident |
| `retrieve_latency` | Time before a resident state is released |
| `load_efficiency` | Probability of successful loading |
| `retrieve_efficiency` | Probability of successful retrieval |
| `t1` | Amplitude-damping timescale, optional |
| `t2` | Dephasing timescale, optional; must satisfy `T2 <= 2*T1` when both exist |
| `maximum_hold` | Hard storage expiration, optional |

### Measurement device

| Field | Meaning |
|---|---|
| `basis_switch_latency` | Time to configure the requested BB84 basis |
| `measurement_latency` | Time from configured device to completed measurement |
| `measurement_fidelity` | Probability that the ideal result is retained |
| `dead_time` | Minimum interval before another operation starts |

## `hardware.prover`

The prover has a QND presence detector, memory, and measurement device. Its memory and
measurement schema match `v0`.

### QND presence detector

| Field | Meaning |
|---|---|
| `operation_latency` | Presence-test duration |
| `efficiency` | Probability of detecting a present challenge |
| `dark_count_rate_hz` | Poisson false-detection rate |
| `state_survival_probability` | Probability a detected state survives the operation |
| `disturbance_probability` | Probability of state disturbance |
| `dead_time` | Detector recovery interval |
| `gate_width` | Presence-detection window |

This is an abstract probabilistic QND model, not an optical pulse or wave-packet model.

## `links`

Quantum links are directional and include attenuation, state fidelity, and source-rate
constraints. Classical links are also directional and may include sender-side delay.
All classical directions required by the QPV protocol must exist.

```yaml
links:
  quantum:
    - id: v0-prover-q
      source: v0
      destination: prover
      attenuation_db_per_m: 0.0002
      polarization_fidelity: 0.995
      frequency_hz: 8.0e7
  classical:
    - id: v0-prover-c
      source: v0
      destination: prover
      sender_delay: 0 ns
```

The physical propagation delay is derived from the configured length and propagation
speed. Attack-added delay is kept separate in trace records.

## `protocol`

| Field | Meaning |
|---|---|
| `basis_function` | `xor`, so basis bit is `x XOR y` |
| `challenge_to_basis_delay` | Intended challenge-to-basis separation at the claimed position |
| `commitment_window` | QND gate/commitment timing allowance |
| `response_slack` | Extra response deadline allowance |
| `minimum_committed_rounds` | Minimum committed rounds for session acceptance |
| `maximum_qber` | Maximum conditional QBER |
| `maximum_timing_violations` | Allowed critical timing violations |
| `maximum_authenticated_radius_m` | Policy geofence radius |
| `initial_start` | Planned start time of the first round |

## `controller`

`policy` is either `baseline` or `security_aware`. The security-aware policy validates
telemetry freshness, reported memory bounds, clock uncertainty, and basis skew before
accepting a plan or report.

```yaml
controller:
  policy: security_aware
  calibration_age_limit: 60 s
  clock_uncertainty: 50 ns
  maximum_reported_t2: 100 us
  maximum_basis_skew: 100 ns
```

## Attacks

Attack objects are applied in YAML order. Each has a stable `id` copied into trace
records.

### Schedule skew

```yaml
- type: schedule_skew
  id: early-basis
  x_shift: -1 us
  y_shift: -1 us
  challenge_shift: 0 ns
  modify_controller_view: false
```

### Telemetry poisoning

```yaml
- type: telemetry_poisoning
  id: inflated-t2
  resource_id: prover.memory
  fields:
    t2_ps: 50000000
    maximum_hold_ps: 80000000
```

### Timestamp forgery

```yaml
- type: timestamp_forgery
  id: forged-v0-time
  node_id: v0
  bias: -500 ns
  fields: [commitment_arrival, answer_arrival]
```

### Selective jamming

```yaml
- type: selective_jamming
  id: jam-v1-basis
  link_ids: [v1-prover]
  message_types: [basis_y]
  start: 0 ns
  end: 20 ms
  drop_probability: 0.2
  added_delay: 1 us
  quantum: false
```

### Intercept–measure–resend

```yaml
- type: intercept_resend
  id: intercept-a0
  position_m: -500
  basis_strategy: random
  processing_latency: 500 ns
  preparation_latency: 100 ns
  replacement_source_fidelity: 1.0
```

## `output`

```yaml
output:
  directory: runs/experiment-name
  trace_level: full
  write_round_csv: true
  write_event_ndjson: true
```

A successful run writes atomically to the requested directory. A failed run is retained
under a `.failed` suffix with the manifest, exception, and partial trace.

## Validation command

Always validate edited configurations before launching a sweep:

```bash
qorchsim validate configs/qpv_noisy.yaml
```
