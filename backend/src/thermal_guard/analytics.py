"""Adaptive point-sensor and thermal-frame analytics."""

import math
from dataclasses import dataclass
from uuid import uuid4

from .config import Settings
from .models import Alert, AlertCause, FrameSummary, SensorReading, Severity, utc_now


@dataclass
class Baseline:
    mean: float
    variance: float = 1.0
    samples: int = 1

    @property
    def standard_deviation(self) -> float:
        return max(0.5, math.sqrt(self.variance))

    def score(self, value: float) -> float:
        return (value - self.mean) / self.standard_deviation

    def update(self, value: float, alpha: float) -> None:
        previous_mean = self.mean
        self.mean = alpha * value + (1 - alpha) * self.mean
        residual = value - previous_mean
        self.variance = alpha * residual * residual + (1 - alpha) * self.variance
        self.samples += 1


class ThermalAnalyzer:
    """Stateful anomaly detector with an adaptive baseline per measurement point."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._baselines: dict[tuple[str, str], Baseline] = {}

    def evaluate(self, reading: SensorReading) -> Alert | None:
        key = (reading.device_id, reading.sensor_id)
        baseline = self._baselines.get(key)
        if baseline is None:
            self._baselines[key] = Baseline(mean=reading.temperature_c)
            z_score = 0.0
            adaptive_threshold = reading.temperature_c
            baseline_samples = 1
        else:
            z_score = baseline.score(reading.temperature_c)
            adaptive_threshold = (
                baseline.mean
                + self.settings.anomaly_z_warning * baseline.standard_deviation
            )
            baseline_samples = baseline.samples
            baseline.update(reading.temperature_c, self.settings.baseline_alpha)

        critical = reading.temperature_c >= self.settings.absolute_critical_c
        absolute_warning = reading.temperature_c >= self.settings.absolute_warning_c
        adaptive_warning = (
            baseline is not None
            and baseline_samples >= 8
            and z_score >= self.settings.anomaly_z_warning
        )
        warning = absolute_warning or adaptive_warning
        if not (critical or warning):
            return None

        severity = Severity.CRITICAL if critical else Severity.WARNING
        if critical:
            cause = AlertCause.ABSOLUTE_CRITICAL
            threshold = self.settings.absolute_critical_c
        elif absolute_warning:
            cause = AlertCause.ABSOLUTE_WARNING
            threshold = self.settings.absolute_warning_c
        else:
            cause = AlertCause.ADAPTIVE
            threshold = adaptive_threshold

        cause_label = cause.value.replace("_", " ")
        return Alert(
            id=str(uuid4()),
            device_id=reading.device_id,
            sensor_id=reading.sensor_id,
            severity=severity,
            temperature_c=reading.temperature_c,
            threshold_c=threshold,
            z_score=round(z_score, 3),
            cause=cause,
            message=f"{reading.sensor_id} {cause_label}",
            created_at=utc_now(),
        )

    @staticmethod
    def summarize_frame(width: int, height: int, pixels: list[float]) -> FrameSummary:
        maximum = max(pixels)
        hotspot_index = pixels.index(maximum)
        return FrameSummary(
            width=width,
            height=height,
            pixels_c=pixels,
            minimum_c=min(pixels),
            maximum_c=maximum,
            hotspot_x=hotspot_index % width,
            hotspot_y=hotspot_index // width,
        )
