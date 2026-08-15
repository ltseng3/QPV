"""Configuration holder for a physical intercept-measure-resend attack."""

from __future__ import annotations

from qorchsim.attacks.base import IdentityAttack


class InterceptResendAttack(IdentityAttack):
    """Attack executed by the QPV runtime through real quantum operations."""

    def __init__(
        self,
        attack_id: str,
        *,
        position_m: float,
        basis_strategy: str = "random",
        processing_latency_ps: int = 500_000,
        preparation_latency_ps: int = 100_000,
        replacement_source_fidelity: float = 1.0,
    ) -> None:
        if basis_strategy not in {"random", "z_only", "x_only"}:
            raise ValueError("unsupported intercept basis strategy")
        self.attack_id = attack_id
        self.position_m = position_m
        self.basis_strategy = basis_strategy
        self.processing_latency_ps = processing_latency_ps
        self.preparation_latency_ps = preparation_latency_ps
        self.replacement_source_fidelity = replacement_source_fidelity
