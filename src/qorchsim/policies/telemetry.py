"""Telemetry policy decisions."""

from __future__ import annotations

from dataclasses import dataclass

from qorchsim.cloudsim.resources import ResourceSnapshot
from qorchsim.qpv.models import PolicyDecision


@dataclass(frozen=True, slots=True)
class TelemetryBounds:
    maximum_t2_ps: int | None = None
    maximum_hold_ps: int | None = None
    maximum_calibration_age_ps: int | None = None


class BaselineTelemetryPolicy:
    """Accept schema-valid telemetry."""

    def validate(self, snapshot: ResourceSnapshot, now_ps: int) -> PolicyDecision:
        return PolicyDecision(True)


class SecurityTelemetryPolicy:
    """Reject implausible or stale reported capability data."""

    def __init__(self, bounds: TelemetryBounds) -> None:
        self.bounds = bounds

    def validate(self, snapshot: ResourceSnapshot, now_ps: int) -> PolicyDecision:
        reasons: list[str] = []
        for device in snapshot.devices:
            reported = device.reported_capabilities
            physical = device.physical_capabilities
            t2 = reported.get("t2_ps")
            if self.bounds.maximum_t2_ps is not None and isinstance(t2, int) and t2 > self.bounds.maximum_t2_ps:
                reasons.append(f"reported_t2_out_of_bounds:{device.resource_id}")
            if isinstance(t2, int) and isinstance(physical.get("t2_ps"), int) and t2 > int(physical["t2_ps"]) * 2:
                reasons.append(f"reported_t2_profile_mismatch:{device.resource_id}")
        return PolicyDecision(not reasons, tuple(reasons))
