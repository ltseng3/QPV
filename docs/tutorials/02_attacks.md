# Tutorial 2: Security Attacks

## Schedule skew

```bash
qorchsim run configs/attacks/schedule_skew.yaml -o runs/skew
```

The attack shifts basis transmissions earlier while preserving the controller's
original expectation. `rounds.csv` records both physical and controller-inferred
commitment margins.

## Telemetry poisoning

```bash
qorchsim run configs/attacks/telemetry_poisoning.yaml -o runs/telemetry
```

The physical memory still evolves with its actual `T2`; only the scheduler-visible
resource snapshot is modified.

## Timestamp forgery

```bash
qorchsim run configs/attacks/timestamp_forgery.yaml -o runs/forgery
```

The trace preserves physical and local timestamps. The attack changes only report
fields. Set `controller.policy: security_aware` to reject biases beyond configured
clock uncertainty.

## Selective jamming

```bash
qorchsim run configs/attacks/selective_jamming.yaml -o runs/jamming
```

Jamming is a link-level delay/drop model, not an RF propagation model.

## Intercept-measure-resend

```bash
qorchsim run configs/attacks/intercept_resend.yaml -o runs/intercept
```

The attacker measures the actual challenge state, prepares a replacement, and sends
it to the prover. With ideal BB84 settings and a random attack basis, the measured
QBER should approach 25%.
