"""Synthetic equipment used by the tests and the demo.

The simulator is deliberately hostile to the algorithm: every point gets a
different, unknown emissivity gain, and faults are injected on top of large
common-mode swings. If the engine can only pass by rejecting common mode, the
tests mean something.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass, field

from .types import Reading

__all__ = ["Point", "Rig", "drive_row", "three_phase_panel"]


@dataclass
class Point:
    """A simulated surface with an unknown emissivity gain."""

    point_id: str
    gain: float
    """Emissivity x view factor. The engine never learns this number."""
    tau_s: float = 240.0
    fault_k: float = 0.0
    """Extra true rise applied to this point only."""
    noise_k: float = 0.06
    _rise: float = field(default=0.0, repr=False)

    def step(self, drive_k: float, dt_s: float, rng: random.Random) -> float:
        """Advance the first-order thermal model, return the apparent rise."""
        target = drive_k + self.fault_k
        alpha = 1.0 - math.exp(-dt_s / self.tau_s)
        self._rise += alpha * (target - self._rise)
        return self.gain * self._rise + rng.gauss(0.0, self.noise_k)


@dataclass
class Rig:
    points: list[Point]
    ambient_c: float = 25.0
    dt_s: float = 4.0
    seed: int = 0
    _t: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    @property
    def point_ids(self) -> list[str]:
        return [p.point_id for p in self.points]

    def sweep(self, drive_k: float, ambient_c: float | None = None) -> list[Reading]:
        amb = self.ambient_c if ambient_c is None else ambient_c
        self._t += self.dt_s
        return [
            Reading(
                point_id=p.point_id,
                temp_c=amb + p.step(drive_k, self.dt_s, self._rng),
                ambient_c=amb,
                t_s=self._t,
            )
            for p in self.points
        ]

    def run(
        self, cycles: int, drive_k: float, ambient_c: float | None = None
    ) -> Iterator[list[Reading]]:
        for _ in range(cycles):
            yield self.sweep(drive_k, ambient_c)

    def settle(self, drive_k: float) -> None:
        """Jump every point straight to steady state, skipping the thermal lag."""
        for p in self.points:
            p._rise = drive_k + p.fault_k


def three_phase_panel(seed: int = 1) -> Rig:
    """Three breaker lugs: bare copper, oxidised copper, painted bus. Same load."""
    return Rig(
        points=[
            Point("L1", gain=0.55, tau_s=260.0),   # bright copper, terrible emitter
            Point("L2", gain=0.95, tau_s=250.0),   # oxidised, near-blackbody
            Point("L3", gain=0.72, tau_s=255.0),   # painted lug
        ],
        seed=seed,
    )


def drive_row(n: int = 6, seed: int = 2) -> Rig:
    """A row of identical VFDs with mildly varying finishes."""
    rng = random.Random(seed)
    return Rig(
        points=[
            Point(
                f"VFD{i + 1}",
                gain=rng.uniform(0.6, 0.95),
                tau_s=rng.uniform(200, 300),
            )
            for i in range(n)
        ],
        seed=seed,
    )
