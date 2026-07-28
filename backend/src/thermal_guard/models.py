"""Validated API and telemetry models."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class Transport(StrEnum):
    HTTP = "http"
    MQTT = "mqtt"
    CAMERA = "camera"


class Severity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCause(StrEnum):
    ABSOLUTE_WARNING = "absolute_warning"
    ABSOLUTE_CRITICAL = "absolute_critical"
    ADAPTIVE = "adaptive"


class SensorReading(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    sensor_id: str = Field(min_length=1, max_length=80)
    temperature_c: float = Field(ge=-273.15, le=2000)
    ambient_c: float | None = Field(default=None, ge=-100, le=150)
    timestamp: datetime = Field(default_factory=utc_now)
    transport: Transport = Transport.HTTP


class DeviceTelemetry(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    firmware_version: str = Field(default="unknown", max_length=40)
    uptime_s: int = Field(default=0, ge=0)
    rssi_dbm: int | None = Field(default=None, ge=-150, le=10)
    readings: list[SensorReading] = Field(min_length=1, max_length=64)
    timestamp: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def normalize_device_ids(self) -> "DeviceTelemetry":
        for reading in self.readings:
            if reading.device_id != self.device_id:
                raise ValueError("all readings must use the telemetry device_id")
        return self


class ThermalFrame(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    camera_id: str = Field(default="thermal-camera", min_length=1, max_length=80)
    width: int = Field(ge=1, le=160)
    height: int = Field(ge=1, le=120)
    pixels_c: list[float] = Field(min_length=1, max_length=19200)
    timestamp: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_shape(self) -> "ThermalFrame":
        expected = self.width * self.height
        if len(self.pixels_c) != expected:
            raise ValueError(f"pixels_c contains {len(self.pixels_c)} values; expected {expected}")
        if any(value < -273.15 or value > 2000 for value in self.pixels_c):
            raise ValueError("thermal frame contains an out-of-range temperature")
        return self


class Alert(BaseModel):
    id: str
    device_id: str
    sensor_id: str
    severity: Severity
    temperature_c: float
    threshold_c: float
    z_score: float
    cause: AlertCause
    message: str
    created_at: datetime
    acknowledged: bool = False


class DeviceSummary(BaseModel):
    device_id: str
    last_seen: datetime
    firmware_version: str
    online: bool
    rssi_dbm: int | None


class FrameSummary(BaseModel):
    width: int
    height: int
    pixels_c: list[float]
    minimum_c: float
    maximum_c: float
    hotspot_x: int
    hotspot_y: int


class DashboardSnapshot(BaseModel):
    device_count: int
    online_count: int
    warning_count: int
    uptime_percent: float | None
    latest_readings: list[SensorReading]
    alerts: list[Alert]
    frame: FrameSummary | None = None
