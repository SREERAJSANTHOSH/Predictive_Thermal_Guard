"""Application service that connects ingestion, analytics, storage, and live clients."""

from collections.abc import Awaitable, Callable

from .analytics import ThermalAnalyzer
from .models import (
    Alert,
    DashboardSnapshot,
    DeviceTelemetry,
    SensorReading,
    ThermalFrame,
)
from .storage import Repository

Broadcaster = Callable[[DashboardSnapshot], Awaitable[None]]


class ThermalGuardService:
    def __init__(
        self,
        repository: Repository,
        analyzer: ThermalAnalyzer,
        broadcaster: Broadcaster | None = None,
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer
        self.broadcaster = broadcaster

    async def ingest_reading(self, reading: SensorReading) -> Alert | None:
        self.repository.add_reading(reading)
        alert = self.analyzer.evaluate(reading)
        if alert is not None:
            self.repository.add_alert(alert)
        await self._broadcast()
        return alert

    async def ingest_telemetry(self, telemetry: DeviceTelemetry) -> list[Alert]:
        self.repository.upsert_device(
            telemetry.device_id,
            telemetry.timestamp,
            firmware_version=telemetry.firmware_version,
            uptime_s=telemetry.uptime_s,
            rssi_dbm=telemetry.rssi_dbm,
        )
        alerts: list[Alert] = []
        for reading in telemetry.readings:
            self.repository.add_reading(reading)
            alert = self.analyzer.evaluate(reading)
            if alert is not None:
                self.repository.add_alert(alert)
                alerts.append(alert)
        await self._broadcast()
        return alerts

    async def ingest_frame(self, frame: ThermalFrame) -> Alert | None:
        summary = self.analyzer.summarize_frame(frame.width, frame.height, frame.pixels_c)
        self.repository.add_frame(frame.device_id, frame.timestamp, summary)
        hotspot = SensorReading(
            device_id=frame.device_id,
            sensor_id=f"{frame.camera_id}:hotspot",
            temperature_c=summary.maximum_c,
            timestamp=frame.timestamp,
            transport="camera",
        )
        self.repository.add_reading(hotspot)
        alert = self.analyzer.evaluate(hotspot)
        if alert is not None:
            self.repository.add_alert(alert)
        await self._broadcast()
        return alert

    def dashboard(self) -> DashboardSnapshot:
        devices = self.repository.list_devices()
        alerts = self.repository.list_alerts(limit=20)
        return DashboardSnapshot(
            device_count=len(devices),
            online_count=sum(device.online for device in devices),
            warning_count=sum(not alert.acknowledged for alert in alerts),
            # A single latest-seen timestamp is insufficient to calculate
            # availability. Keep the value unknown until heartbeat history is
            # stored and evaluated over a defined observation window.
            uptime_percent=None,
            latest_readings=self.repository.latest_readings(),
            alerts=alerts,
            frame=self.repository.latest_frame(),
        )

    async def _broadcast(self) -> None:
        if self.broadcaster is not None:
            await self.broadcaster(self.dashboard())
