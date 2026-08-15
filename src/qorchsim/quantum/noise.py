"""Time-dependent memory and component noise."""

from __future__ import annotations

import math

from qorchsim.quantum.kraus import amplitude_damping, phase_damping_from_coherence


def memory_channels(elapsed_ps: int, t1_ps: int | None, t2_ps: int | None):
    """Build sequential memory-noise channels for elapsed storage time."""
    channels = []
    elapsed = max(0, elapsed_ps)
    if t1_ps is not None and t1_ps > 0:
        channels.append(amplitude_damping(1.0 - math.exp(-elapsed / t1_ps)))
    if t2_ps is not None and t2_ps > 0:
        if t1_ps is None:
            coherence = math.exp(-elapsed / t2_ps)
        else:
            inv_tphi = max(0.0, 1.0 / t2_ps - 1.0 / (2.0 * t1_ps))
            coherence = math.exp(-elapsed * inv_tphi) if inv_tphi > 0 else 1.0
        channels.append(phase_damping_from_coherence(coherence))
    return channels
