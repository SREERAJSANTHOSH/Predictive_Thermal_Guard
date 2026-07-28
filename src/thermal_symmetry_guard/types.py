"""Shared value types for Thermal Symmetry Guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Verdict",
    "GroupMode",
    "Reading",
    "ChannelReport",
    "GroupReport",
]


class Verdict(str, Enum):
    """Per-channel conclusion emitted every cycle."""

    WARMING_UP = "warming_up"
    SYMMETRIC = "symmetric"
    COMMON_MODE_RISE = "common_mode_rise"
    ASYMMETRIC_HOT = "asymmetric_hot"
    ASYMMETRIC_COLD = "asymmetric_cold"
    TAU_SHIFT = "tau_shift"
    SENSOR_SUSPECT = "sensor_suspect"


class GroupMode(str, Enum):
    """How the reference signal for a group is being derived."""

    PEER_MEDIAN = "peer_median"      # >=3 healthy peers: full common-mode rejection
    SELF_HISTORY = "self_history"    # <3 peers: fall back to each point's own baseline


@dataclass(frozen=True)
class Reading:
    """One raw sample from one monitored point.

    ``temp_c`` is the *uncorrected* IR reading straight off the sensor.
    No emissivity setting is required or used anywhere in this system.
    """

    point_id: str
    temp_c: float
    ambient_c: float
    t_s: float


@dataclass
class ChannelReport:
    point_id: str
    verdict: Verdict
    temp_c: float
    rise_k: float
    """Apparent rise above ambient, in kelvin. Emissivity-scaled, never trusted absolutely."""
    asymmetry: float
    """Log-domain differential mode. 0.0 == perfectly in step with peers."""
    robust_z: float
    """Asymmetry expressed in robust sigmas of this channel's own quiet history."""
    cusum: float
    """Accumulated one-sided drift score for slow, sub-threshold divergence."""
    tau_s: float | None = None
    """Cooldown thermal time constant, seconds. None until a cooldown is observed."""
    tau_ratio: float | None = None
    """tau_s / baseline tau. <1 means the point now sheds heat faster than it used to."""
    detail: str = ""


@dataclass
class GroupReport:
    group_id: str
    mode: GroupMode
    common_mode: float
    """Shared log-domain drive level: load and ambient, with per-point offsets removed."""
    common_mode_rising: bool
    channels: list[ChannelReport] = field(default_factory=list)

    @property
    def worst(self) -> ChannelReport | None:
        if not self.channels:
            return None
        return max(self.channels, key=lambda c: abs(c.robust_z))
