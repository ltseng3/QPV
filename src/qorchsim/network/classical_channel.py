"""Attackable event-driven classical channel."""

from __future__ import annotations

from collections.abc import Callable

from qorchsim.attacks.base import AttackContext
from qorchsim.attacks.pipeline import AttackPipeline
from qorchsim.core.events import DomainEvent, EventPhase
from qorchsim.core.identifiers import stable_id
from qorchsim.core.scheduler import EventScheduler
from qorchsim.network.transmissions import ClassicalTransmission
from qorchsim.types import SimTimePs


class AttackableClassicalChannel:
    """Deliver immutable messages after attack transformation and propagation."""

    EVENT_ARRIVAL = "network.classical.arrival"

    def __init__(
        self,
        scheduler: EventScheduler,
        attacks: AttackPipeline,
        deliver: Callable[[ClassicalTransmission], None],
    ) -> None:
        self.scheduler = scheduler
        self.attacks = attacks
        self.deliver = deliver

    def send(self, transmission: ClassicalTransmission, context: AttackContext) -> tuple[ClassicalTransmission, ...]:
        outputs = self.attacks.alter_classical(transmission, context)
        for index, output in enumerate(outputs):
            if output.dropped:
                continue
            event_id = stable_id("classical-arrival", output.transmission_id, index, output.arrival_time_ps)
            self.scheduler.schedule_at(
                SimTimePs(output.arrival_time_ps),
                EventPhase.PHYSICAL_ARRIVAL,
                DomainEvent(event_id, self.EVENT_ARRIVAL, output),
            )
        return outputs
