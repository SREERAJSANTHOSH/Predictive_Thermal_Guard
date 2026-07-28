"""Small robust-statistics helpers.

Everything here is O(1) memory per channel or bounded by a small ring buffer,
so the same logic ports directly to an ESP32 with no dynamic allocation.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Iterable, Sequence

__all__ = ["median", "mad", "RobustBaseline", "Cusum", "TrendFilter"]

_MAD_TO_SIGMA = 1.4826
"""Scale factor making MAD a consistent estimator of sigma for Gaussian noise."""


def median(values: Sequence[float]) -> float:
    """Median of a non-empty sequence."""
    if not values:
        raise ValueError("median() of empty sequence")
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def mad(values: Sequence[float], center: float | None = None) -> float:
    """Median absolute deviation, unscaled."""
    if not values:
        raise ValueError("mad() of empty sequence")
    c = median(values) if center is None else center
    return median([abs(v - c) for v in values])


class RobustBaseline:
    """Rolling median/MAD over a fixed window, used as each channel's quiet reference.

    A hard floor on sigma is mandatory: temperatures are quantised, so a
    perfectly flat window has MAD exactly 0 and every subsequent LSB of noise
    would otherwise score as an infinite z. The floor is expressed in the same
    units as the fed values.
    """

    def __init__(self, window: int = 64, sigma_floor: float = 0.02) -> None:
        if window < 3:
            raise ValueError("window must be >= 3")
        if sigma_floor <= 0.0:
            raise ValueError("sigma_floor must be > 0")
        self.window = window
        self.sigma_floor = sigma_floor
        self._buf: deque[float] = deque(maxlen=window)

    def feed(self, value: float) -> None:
        if math.isfinite(value):
            self._buf.append(value)

    def extend(self, values: Iterable[float]) -> None:
        for v in values:
            self.feed(v)

    @property
    def count(self) -> int:
        return len(self._buf)

    @property
    def ready(self) -> bool:
        """True once there are enough samples for median/MAD to mean anything."""
        return len(self._buf) >= max(8, self.window // 4)

    @property
    def center(self) -> float:
        return median(list(self._buf)) if self._buf else 0.0

    @property
    def sigma(self) -> float:
        if len(self._buf) < 3:
            return self.sigma_floor
        s = _MAD_TO_SIGMA * mad(list(self._buf))
        return max(s, self.sigma_floor)

    def z(self, value: float) -> float:
        """Robust z-score of ``value`` against the window. Always finite."""
        if not math.isfinite(value):
            return 0.0
        return (value - self.center) / self.sigma

    def reset(self) -> None:
        self._buf.clear()


class Cusum:
    """Two-sided tabular CUSUM for slow drift that never trips a z threshold.

    ``slack`` (k) is the drift magnitude in sigmas that is deliberately ignored;
    ``limit`` (h) is the alarm level. Classic choice k=0.5, h=5.0 detects a
    sustained 1-sigma shift in roughly ten samples while surviving noise.
    """

    def __init__(self, slack: float = 0.5, limit: float = 5.0) -> None:
        if slack < 0.0:
            raise ValueError("slack must be >= 0")
        if limit <= 0.0:
            raise ValueError("limit must be > 0")
        self.slack = slack
        self.limit = limit
        self.high = 0.0
        self.low = 0.0

    def feed(self, z: float) -> float:
        """Feed a z-score, return the signed accumulator (positive side wins ties)."""
        if not math.isfinite(z):
            z = 0.0
        self.high = max(0.0, self.high + z - self.slack)
        self.low = min(0.0, self.low + z + self.slack)
        return self.high if self.high >= -self.low else self.low

    @property
    def value(self) -> float:
        return self.high if self.high >= -self.low else self.low

    @property
    def tripped(self) -> bool:
        return self.high >= self.limit or -self.low >= self.limit

    def reset(self) -> None:
        self.high = 0.0
        self.low = 0.0


class TrendFilter:
    """Double-exponential (Holt) smoother with an explicit warm-up.

    Kept deliberately minimal: it reports level and slope per second, and it
    refuses to extrapolate before it has seen enough samples to have a slope.
    """

    def __init__(self, alpha: float = 0.3, beta: float = 0.1, warmup: int = 4) -> None:
        if not 0.0 < alpha <= 1.0 or not 0.0 <= beta <= 1.0:
            raise ValueError("alpha must be in (0,1] and beta in [0,1]")
        self.alpha = alpha
        self.beta = beta
        self.warmup = warmup
        self.level: float | None = None
        self.slope: float = 0.0
        self.n = 0
        self._last_t: float | None = None

    def feed(self, value: float, t_s: float) -> None:
        self.n += 1
        if self.level is None or self._last_t is None:
            self.level = value
            self.slope = 0.0
            self._last_t = t_s
            return
        dt = max(1e-6, t_s - self._last_t)
        prev = self.level
        self.level = self.alpha * value + (1.0 - self.alpha) * (prev + self.slope * dt)
        self.slope = self.beta * ((self.level - prev) / dt) + (1.0 - self.beta) * self.slope
        self._last_t = t_s

    @property
    def ready(self) -> bool:
        return self.n >= self.warmup

    @property
    def slope_per_s(self) -> float:
        return self.slope if self.ready else 0.0

    def reset(self) -> None:
        self.level = None
        self.slope = 0.0
        self.n = 0
        self._last_t = None
