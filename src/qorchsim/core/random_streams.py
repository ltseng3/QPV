"""Named reproducible NumPy random streams."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
from numpy.random import Generator

from qorchsim.errors import DuplicateEventError


@dataclass
class RandomStreams:
    """Derive independent named generators from one master seed."""

    master_seed: int
    strict: bool = False
    _generators: dict[str, Generator] = field(default_factory=dict, init=False)
    _owners: dict[str, str] = field(default_factory=dict, init=False)

    def generator(self, name: str, *, owner: str | None = None) -> Generator:
        if name in self._generators:
            if self.strict and owner is not None and self._owners.get(name) not in (None, owner):
                raise DuplicateEventError(f"random stream {name!r} already owned")
            return self._generators[name]
        digest = hashlib.sha256(f"{self.master_seed}:{name}".encode()).digest()
        entropy = [self.master_seed, *np.frombuffer(digest[:16], dtype=np.uint32).tolist()]
        generator = np.random.default_rng(np.random.SeedSequence(entropy))
        self._generators[name] = generator
        if owner is not None:
            self._owners[name] = owner
        return generator
