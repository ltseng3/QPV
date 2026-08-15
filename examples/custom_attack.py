"""Minimal example of a reusable message-layer attack.

The example exercises the attack contract directly. To expose a new attack through YAML,
add a Pydantic configuration model and construct it in
``qorchsim.experiments.runner._attack_pipeline``.
"""

from __future__ import annotations

from qorchsim.attacks.base import AttackContext, IdentityAttack
from qorchsim.network.transmissions import ClassicalTransmission
from qorchsim.core.random_streams import RandomStreams


class DuplicateCommitmentAttack(IdentityAttack):
    """Replay every commitment once after a fixed delay."""

    attack_id = "duplicate-commitment"

    def __init__(self, replay_delay_ps: int) -> None:
        self.replay_delay_ps = replay_delay_ps

    def alter_classical(
        self,
        tx: ClassicalTransmission,
        ctx: AttackContext,
    ) -> tuple[ClassicalTransmission, ...]:
        if tx.message_type != "commitment":
            return (tx,)
        replay = tx.with_attack(
            self.attack_id,
            transmission_id=f"{tx.transmission_id}-replay",
            added_delay_ps=tx.added_delay_ps + self.replay_delay_ps,
        )
        return tx, replay


def main() -> None:
    original = ClassicalTransmission(
        transmission_id="commit-1",
        link_id="prover-v0",
        source="prover",
        destination="v0",
        message_type="commitment",
        payload={"round_id": "round-000001", "committed": True},
        send_time_ps=1_000_000,
        propagation_delay_ps=5_000_000,
    )
    context = AttackContext(
        now_ps=original.send_time_ps,
        session_id="session-0",
        round_id="round-000001",
        rng=RandomStreams(7).generator("example/duplicate-commitment"),
    )
    outputs = DuplicateCommitmentAttack(250_000).alter_classical(original, context)
    for output in outputs:
        print(output.transmission_id, output.arrival_time_ps, output.attack_ids)


if __name__ == "__main__":
    main()
