"""Small SQLite repository with no external database dependency."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import (
    Alert,
    DeviceSummary,
    FrameSummary,
    SensorReading,
    Severity,
    Transport,
)


class Repository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if database_path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_connection.row_factory = sqlite3.Row

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            yield self._memory_connection
            self._memory_connection.commit()
            return
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    last_seen TEXT NOT NULL,
                    firmware_version TEXT NOT NULL,
                    uptime_s INTEGER NOT NULL,
                    rssi_dbm INTEGER
                );
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    ambient_c REAL,
                    timestamp TEXT NOT NULL,
                    transport TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_readings_latest
                    ON readings(device_id, sensor_id, timestamp DESC);
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    threshold_c REAL NOT NULL,
                    z_score REAL NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    acknowledged INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    pixels_json TEXT NOT NULL,
                    minimum_c REAL NOT NULL,
                    maximum_c REAL NOT NULL,
                    hotspot_x INTEGER NOT NULL,
                    hotspot_y INTEGER NOT NULL
                );
                """
            )

    def upsert_device(
        self,
        device_id: str,
        timestamp: datetime,
        firmware_version: str = "unknown",
        uptime_s: int = 0,
        rssi_dbm: int | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO devices(device_id, last_seen, firmware_version, uptime_s, rssi_dbm)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    firmware_version = CASE
                        WHEN excluded.firmware_version = 'unknown'
                        THEN devices.firmware_version
                        ELSE excluded.firmware_version
                    END,
                    uptime_s = MAX(devices.uptime_s, excluded.uptime_s),
                    rssi_dbm = COALESCE(excluded.rssi_dbm, devices.rssi_dbm)
                """,
                (device_id, timestamp.isoformat(), firmware_version, uptime_s, rssi_dbm),
            )

    def add_reading(self, reading: SensorReading) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO readings(
                    device_id, sensor_id, temperature_c, ambient_c, timestamp, transport
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    reading.device_id,
                    reading.sensor_id,
                    reading.temperature_c,
                    reading.ambient_c,
                    reading.timestamp.isoformat(),
                    reading.transport.value,
                ),
            )
        self.upsert_device(reading.device_id, reading.timestamp)

    def add_alert(self, alert: Alert) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO alerts(
                    id, device_id, sensor_id, severity, temperature_c, threshold_c,
                    z_score, message, created_at, acknowledged
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.id,
                    alert.device_id,
                    alert.sensor_id,
                    alert.severity.value,
                    alert.temperature_c,
                    alert.threshold_c,
                    alert.z_score,
                    alert.message,
                    alert.created_at.isoformat(),
                    int(alert.acknowledged),
                ),
            )

    def add_frame(self, device_id: str, timestamp: datetime, frame: FrameSummary) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO frames(
                    device_id, timestamp, width, height, pixels_json, minimum_c,
                    maximum_c, hotspot_x, hotspot_y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    timestamp.isoformat(),
                    frame.width,
                    frame.height,
                    json.dumps(frame.pixels_c, separators=(",", ":")),
                    frame.minimum_c,
                    frame.maximum_c,
                    frame.hotspot_x,
                    frame.hotspot_y,
                ),
            )
        self.upsert_device(device_id, timestamp)

    def list_devices(self) -> list[DeviceSummary]:
        online_after = datetime.now(UTC) - timedelta(minutes=2)
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM devices ORDER BY last_seen DESC"
            ).fetchall()
        return [
            DeviceSummary(
                device_id=row["device_id"],
                last_seen=datetime.fromisoformat(row["last_seen"]),
                firmware_version=row["firmware_version"],
                online=datetime.fromisoformat(row["last_seen"]) >= online_after,
                rssi_dbm=row["rssi_dbm"],
            )
            for row in rows
        ]

    def latest_readings(self, limit: int = 64) -> list[SensorReading]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*
                FROM readings r
                INNER JOIN (
                    SELECT device_id, sensor_id, MAX(timestamp) AS latest
                    FROM readings GROUP BY device_id, sensor_id
                ) x ON r.device_id = x.device_id
                   AND r.sensor_id = x.sensor_id
                   AND r.timestamp = x.latest
                ORDER BY r.timestamp DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            SensorReading(
                device_id=row["device_id"],
                sensor_id=row["sensor_id"],
                temperature_c=row["temperature_c"],
                ambient_c=row["ambient_c"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                transport=Transport(row["transport"]),
            )
            for row in rows
        ]

    def list_alerts(self, limit: int = 50) -> list[Alert]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            Alert(
                id=row["id"],
                device_id=row["device_id"],
                sensor_id=row["sensor_id"],
                severity=Severity(row["severity"]),
                temperature_c=row["temperature_c"],
                threshold_c=row["threshold_c"],
                z_score=row["z_score"],
                message=row["message"],
                created_at=datetime.fromisoformat(row["created_at"]),
                acknowledged=bool(row["acknowledged"]),
            )
            for row in rows
        ]

    def latest_frame(self) -> FrameSummary | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM frames ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return FrameSummary(
            width=row["width"],
            height=row["height"],
            pixels_c=json.loads(row["pixels_json"]),
            minimum_c=row["minimum_c"],
            maximum_c=row["maximum_c"],
            hotspot_x=row["hotspot_x"],
            hotspot_y=row["hotspot_y"],
        )
