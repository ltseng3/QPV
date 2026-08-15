"""Local clock with drift, offset, resolution, and observation jitter."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator

from qorchsim.devices.capabilities import ClockCapabilities


class LocalClock:
    """Convert physical simulation time to a node-local observation."""

    def __init__(self, capabilities: ClockCapabilities, rng: Generator) -> None:
        self.capabilities = capabilities
        self.rng = rng

    def observe(self, physical_time_ps: int) -> int:
        c = self.capabilities
        elapsed = physical_time_ps - c.epoch_physical_ps
        drifted = c.epoch_physical_ps + elapsed * (1.0 + c.drift_ppm * 1e-6)
        jitter = float(self.rng.normal(0.0, c.jitter_stddev_ps)) if c.jitter_stddev_ps else 0.0
        value = drifted + c.offset_ps + jitter
        resolution = max(1, c.resolution_ps)
        return int(np.rint(value / resolution) * resolution)
