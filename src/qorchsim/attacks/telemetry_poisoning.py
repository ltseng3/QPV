"""Resource telemetry poisoning."""

from __future__ import annotations

from dataclasses import replace

from qorchsim.attacks.base import AttackContext, IdentityAttack
from qorchsim.cloudsim.resources import DeviceResource, ResourceSnapshot


class TelemetryPoisoningAttack(IdentityAttack):
    """Replace selected reported device attributes without changing physical truth."""

    def __init__(self, attack_id: str, resource_id: str, fields: dict[str, object]) -> None:
        self.attack_id = attack_id
        self.resource_id = resource_id
        self.fields = dict(fields)

    def alter_inventory(self, snapshot: ResourceSnapshot, ctx: AttackContext) -> ResourceSnapshot:
        devices = []
        for device in snapshot.devices:
            if device.resource_id == self.resource_id:
                reported = {**device.reported_capabilities, **self.fields}
                devices.append(replace(device, reported_capabilities=reported, attack_ids=(*device.attack_ids, self.attack_id)))
            else:
                devices.append(device)
        return replace(snapshot, devices=tuple(devices))
