"""The core engine: differential thermography without emissivity calibration.

The premise
-----------
For a surface warmed above its surroundings, an uncalibrated IR sensor reports
an apparent rise above ambient that is, to first order, the true rise scaled by
a constant factor set by emissivity and view factor::

    rise_apparent  =  g * rise_true            (g unknown, roughly constant)

Take logs and the unknown becomes *additive*::

    log(rise_apparent)  =  log(g) + log(rise_true)

``log(g)`` is a per-point constant. Any operation that removes constants also
removes emissivity. This engine removes them twice over:

1. **Peer subtraction.** Subtract the median ``log(rise)`` across a group of
   nominally identical points (the three phases of a breaker, six drives in a
   rack row). Shared load and ambient swings are common-mode and vanish.
2. **Offset subtraction.** Subtract each point's own learned quiet-state
   residual, which absorbs whatever is left of ``log(g)``.

What survives is pure differential mode: "this point is running out of step
with its siblings." That is the signal a thermographer actually acts on, and it
needs no emissivity number, no contact probe, and no calibration session.

Absolute temperatures are still reported, but they are never the basis of a
verdict. They are labelled apparent throughout.
"""

from __future__ import annotations

import math

from .robust import Cusum, RobustBaseline, TrendFilter, median
from .types import ChannelReport, GroupMode, GroupReport, Reading, Verdict

__all__ = ["MIN_RISE_K", "Channel", "SymmetryGroup"]

MIN_RISE_K = 1.5
"""Below this apparent rise above ambient the log transform is noise-dominated.

A point sitting within ~1.5 K of ambient carries no usable thermal signal: the
ratio of two near-zero rises is meaningless, so the engine reports WARMING_UP
rather than inventing an asymmetry.
"""

_MIN_PEERS_FOR_MEDIAN = 3
"""Median needs three points to have a defensible middle when one is faulty."""


def _log_rise(temp_c: float, ambient_c: float) -> float | None:
    """Log-domain apparent rise, or None when the point is too close to ambient."""
    rise = temp_c - ambient_c
    if not math.isfinite(rise) or rise < MIN_RISE_K:
        return None
    return math.log(rise)


class Channel:
    """One monitored point: its offset, its history, and its cooldown signature."""

    def __init__(
        self,
        point_id: str,
        *,
        window: int = 64,
        sigma_floor: float = 0.01,
        cusum_slack: float = 0.5,
        cusum_limit: float = 5.0,
    ) -> None:
        self.point_id = point_id
        self.offset_baseline = RobustBaseline(window=window, sigma_floor=1e-4)
        """Learned quiet-state residual. This is where emissivity goes to die."""
        self.commissioned = False
        """False during the offset-learning phase, when no verdict is issued."""
        self.asym_baseline = RobustBaseline(window=window, sigma_floor=sigma_floor)
        self.cusum = Cusum(slack=cusum_slack, limit=cusum_limit)
        self.trend = TrendFilter()
        self.tau_estimator = TauEstimator()
        self.baseline_tau_s: float | None = None
        self.last_log_rise: float | None = None
        self.quarantined = False
        """Set when the point is judged faulty, so it stops polluting the median."""
        self._stale_cycles = 0

    @property
    def offset(self) -> float:
        """Per-point additive constant in log space; 0.0 until commissioning ends.

        The gate is a *full* window, not merely a usable one. Applying a
        half-learned offset makes the asymmetry signal jump the moment the
        offset firms up, which reads as a fault on a perfectly healthy point.
        """
        return self.offset_baseline.center if self.offset_settled else 0.0

    @property
    def offset_settled(self) -> bool:
        """True once the offset window is full, i.e. commissioning is complete.

        Order matters: the asymmetry baseline must not start learning until the
        offset it is measured against has stopped moving, or the two chase each
        other and every channel looks permanently faulty.
        """
        return self.offset_baseline.count >= self.offset_baseline.window

    def note_missing(self) -> None:
        self._stale_cycles += 1

    def note_present(self) -> None:
        self._stale_cycles = 0

    @property
    def stale(self) -> bool:
        return self._stale_cycles >= 3


class TauEstimator:
    """Recovers the cooldown thermal time constant from a natural cooling episode.

    While a body cools freely toward ambient, its rise decays exponentially, so
    ``log(rise)`` falls linearly with slope ``-1/tau``. Fitting that slope needs
    no emissivity: a multiplicative gain shifts the intercept, not the slope.
    That makes tau the one *absolute*, calibration-free number this system can
    report, and it is a direct read on the thermal path. A loosening bolt, a
    dried thermal pad or a clogged fin stack all lengthen tau long before the
    steady-state temperature moves enough to trip anything.
    """

    def __init__(
        self,
        *,
        min_samples: int = 8,
        min_span_s: float = 30.0,
        min_decay: float = 0.15,
        max_segment: int = 256,
        max_gap_s: float = 60.0,
    ) -> None:
        self.min_samples = min_samples
        self.min_span_s = min_span_s
        self.min_decay = min_decay
        self.max_segment = max_segment
        self.max_gap_s = max_gap_s
        self._t: list[float] = []
        self._y: list[float] = []
        self.tau_s: float | None = None

    def feed(self, t_s: float, log_rise: float | None, cooling: bool) -> float | None:
        """Accumulate a cooling segment and refit continuously.

        The fit is re-evaluated on every sample rather than only when the
        segment closes, so tau is available *during* a cooldown. Equipment
        rarely cools all the way to ambient before restarting, and a tau that
        only appeared after a completed cooldown would almost never appear.
        """
        if not cooling or log_rise is None:
            self._t.clear()
            self._y.clear()
            return None
        # A gap in time means a new cooling episode, not a continuation.
        if self._t and (t_s - self._t[-1]) > self.max_gap_s:
            self._t.clear()
            self._y.clear()
        self._t.append(t_s)
        self._y.append(log_rise)
        if len(self._t) > self.max_segment:
            self._t.pop(0)
            self._y.pop(0)
        return self._fit()

    def _fit(self) -> float | None:
        n = len(self._t)
        if n < self.min_samples:
            return None
        span = self._t[-1] - self._t[0]
        if span < self.min_span_s:
            return None
        if (self._y[0] - self._y[-1]) < self.min_decay:
            return None
        slope = _ols_slope(self._t, self._y)
        if slope is None or slope >= 0.0:
            return None
        tau = -1.0 / slope
        if not math.isfinite(tau) or tau <= 0.0:
            return None
        self.tau_s = tau
        return tau


def _ols_slope(xs: list[float], ys: list[float]) -> float | None:
    """Least-squares slope of y over x. None if x has no spread."""
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0.0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    return sxy / sxx


class SymmetryGroup:
    """A set of nominally identical points evaluated against each other."""

    def __init__(
        self,
        group_id: str,
        point_ids: list[str],
        *,
        z_warn: float = 3.5,
        tau_tolerance: float = 0.25,
        learn_below_z: float = 2.0,
        **channel_kwargs: object,
    ) -> None:
        if not point_ids:
            raise ValueError("a group needs at least one point")
        if len(set(point_ids)) != len(point_ids):
            raise ValueError("duplicate point_id in group")
        self.group_id = group_id
        self.z_warn = z_warn
        self.tau_tolerance = tau_tolerance
        self.learn_below_z = learn_below_z
        self.channels: dict[str, Channel] = {
            pid: Channel(pid, **channel_kwargs) for pid in point_ids  # type: ignore[arg-type]
        }
        self.common_mode_trend = TrendFilter()
        self._last_common: float | None = None

    # ------------------------------------------------------------------ update

    def update(self, readings: list[Reading]) -> GroupReport:
        """Process one synchronous sweep of the group."""
        by_id = {r.point_id: r for r in readings}
        unknown = set(by_id) - set(self.channels)
        if unknown:
            raise KeyError(f"readings for points not in group: {sorted(unknown)}")

        log_rise: dict[str, float | None] = {}
        for pid, ch in self.channels.items():
            reading = by_id.get(pid)
            if reading is None:
                ch.note_missing()
                log_rise[pid] = None
                continue
            ch.note_present()
            log_rise[pid] = _log_rise(reading.temp_c, reading.ambient_c)

        active = [
            pid
            for pid, v in log_rise.items()
            if v is not None and not self.channels[pid].quarantined
        ]
        usable: list[float] = []
        for pid in active:
            value = log_rise[pid]
            if value is not None:
                usable.append(value - self.channels[pid].offset)

        if len(active) >= _MIN_PEERS_FOR_MEDIAN:
            mode = GroupMode.PEER_MEDIAN
            common = median(usable)
        else:
            mode = GroupMode.SELF_HISTORY
            common = median(usable) if usable else 0.0

        t_now = max((r.t_s for r in readings), default=0.0)
        self.common_mode_trend.feed(common, t_now)
        rising = self.common_mode_trend.slope_per_s > 1e-4
        self._last_common = common

        reports = [
            self._evaluate(pid, by_id.get(pid), log_rise[pid], common, mode, rising)
            for pid in self.channels
        ]
        return GroupReport(
            group_id=self.group_id,
            mode=mode,
            common_mode=common,
            common_mode_rising=rising,
            channels=reports,
        )

    # ---------------------------------------------------------------- internal

    def _evaluate(
        self,
        pid: str,
        reading: Reading | None,
        lr: float | None,
        common: float,
        mode: GroupMode,
        rising: bool,
    ) -> ChannelReport:
        ch = self.channels[pid]

        if reading is None or ch.stale:
            return ChannelReport(
                point_id=pid,
                verdict=Verdict.SENSOR_SUSPECT,
                temp_c=reading.temp_c if reading else float("nan"),
                rise_k=float("nan"),
                asymmetry=0.0,
                robust_z=0.0,
                cusum=ch.cusum.value,
                tau_s=ch.tau_estimator.tau_s,
                detail="no reading for 3 consecutive sweeps",
            )

        rise = reading.temp_c - reading.ambient_c
        if lr is None:
            ch.trend.feed(reading.temp_c, reading.t_s)
            ch.last_log_rise = None
            return ChannelReport(
                point_id=pid,
                verdict=Verdict.WARMING_UP,
                temp_c=reading.temp_c,
                rise_k=rise,
                asymmetry=0.0,
                robust_z=0.0,
                cusum=ch.cusum.value,
                tau_s=ch.tau_estimator.tau_s,
                detail=f"apparent rise {rise:.1f} K below the {MIN_RISE_K} K floor",
            )

        # Differential mode: peers out, own offset out, emissivity out.
        asym = (lr - ch.offset) - common
        scoring = ch.offset_settled and ch.asym_baseline.ready
        z = ch.asym_baseline.z(asym) if scoring else 0.0
        cusum_val = ch.cusum.feed(z) if scoring else ch.cusum.value

        # Cooldown signature.
        #
        # Cooling is judged from consecutive log-rise samples rather than the
        # smoothed trend: the smoother lags by several samples after a restart,
        # which truncates the very segment the fit needs.
        ch.trend.feed(reading.temp_c, reading.t_s)
        cooling = ch.last_log_rise is not None and lr < ch.last_log_rise
        new_tau = ch.tau_estimator.feed(reading.t_s, lr, cooling)
        if new_tau is not None and ch.baseline_tau_s is None:
            ch.baseline_tau_s = new_tau
        tau_ratio = (
            ch.tau_estimator.tau_s / ch.baseline_tau_s
            if ch.tau_estimator.tau_s and ch.baseline_tau_s
            else None
        )

        verdict, detail = self._classify(ch, z, cusum_val, tau_ratio, rising, mode)

        # Two-phase learning, in order.
        #
        # Phase 1 (commissioning): fill the offset window unconditionally. The
        # residual lr - common IS the per-point constant, so it must settle
        # before anything is measured against it.
        #
        # Phase 2 (monitoring): the offset is frozen against faults — only
        # quiet cycles feed either window, so a genuine hot spot can never be
        # slowly absorbed into "normal".
        if not ch.offset_settled:
            ch.offset_baseline.feed(lr - common)
        elif abs(z) < self.learn_below_z or not ch.asym_baseline.ready:
            ch.offset_baseline.feed(lr - common)
            ch.asym_baseline.feed(asym)
        if ch.offset_settled:
            ch.commissioned = True

        ch.last_log_rise = lr
        return ChannelReport(
            point_id=pid,
            verdict=verdict,
            temp_c=reading.temp_c,
            rise_k=rise,
            asymmetry=asym,
            robust_z=z,
            cusum=cusum_val,
            tau_s=ch.tau_estimator.tau_s,
            tau_ratio=tau_ratio,
            detail=detail,
        )

    def _classify(
        self,
        ch: Channel,
        z: float,
        cusum_val: float,
        tau_ratio: float | None,
        rising: bool,
        mode: GroupMode,
    ) -> tuple[Verdict, str]:
        if not ch.offset_settled:
            pct = 100 * ch.offset_baseline.count // ch.offset_baseline.window
            return (
                Verdict.WARMING_UP,
                f"commissioning: learning this point's offset ({pct}% complete)",
            )

        if not ch.asym_baseline.ready:
            return (
                Verdict.WARMING_UP,
                f"learning normal spread ({ch.asym_baseline.count} samples)",
            )

        if tau_ratio is not None and abs(tau_ratio - 1.0) > self.tau_tolerance:
            direction = "slower" if tau_ratio > 1.0 else "faster"
            return (
                Verdict.TAU_SHIFT,
                f"cooldown {direction}: tau now {tau_ratio:.2f}x baseline — "
                "thermal path changed, check mounting and airflow",
            )

        if abs(z) >= self.z_warn or ch.cusum.tripped:
            trigger = "step" if abs(z) >= self.z_warn else "sustained drift"
            if z > 0 or cusum_val > 0:
                if mode is GroupMode.SELF_HISTORY:
                    return (
                        Verdict.ASYMMETRIC_HOT,
                        f"{trigger} above own history, z={z:.1f} "
                        "(no peer quorum — treat as provisional)",
                    )
                return (
                    Verdict.ASYMMETRIC_HOT,
                    f"{trigger} above peers, z={z:.1f}, cusum={cusum_val:.1f}",
                )
            return (
                Verdict.ASYMMETRIC_COLD,
                f"{trigger} below peers, z={z:.1f} — check load sharing or a "
                "sensor losing sight of the target",
            )

        if rising:
            return (
                Verdict.COMMON_MODE_RISE,
                "whole group heating together — tracks load or ambient, not a fault",
            )

        return (Verdict.SYMMETRIC, f"in step with peers, z={z:.1f}")

    # ------------------------------------------------------------- maintenance

    def quarantine(self, point_id: str) -> None:
        """Stop a point contributing to the peer median without muting its alarms."""
        self.channels[point_id].quarantined = True

    def release(self, point_id: str) -> None:
        self.channels[point_id].quarantined = False
