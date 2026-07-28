from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class LoggedReading:
    timestamp: datetime
    device_id: str
    channel: int
    temp_c: float
    ambient_c: float | None
    baseline_c: float | None
    deviation_c: float | None
    abnormal: bool
    reason: str

    @property
    def sensor_key(self) -> tuple[str, int]:
        return (self.device_id, self.channel)


def load_readings(path: Path) -> list[LoggedReading]:
    if not path.exists():
        return []

    readings: list[LoggedReading] = []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    readings.append(_parse_row(row))
                except (KeyError, TypeError, ValueError):
                    # The monitor may be writing the final row while the GUI
                    # refreshes. A later refresh will read the complete row.
                    continue
    except OSError:
        return []
    return readings


def _parse_row(row: dict[str, str]) -> LoggedReading:
    return LoggedReading(
        timestamp=datetime.fromisoformat(row["timestamp_utc"]),
        device_id=row["device_id"],
        channel=int(row["channel"]),
        temp_c=float(row["temp_c"]),
        ambient_c=_optional_float(row.get("ambient_c")),
        baseline_c=_optional_float(row.get("baseline_c")),
        deviation_c=_optional_float(row.get("deviation_c")),
        abnormal=row.get("abnormal", "").lower() == "true",
        reason=row.get("reason", ""),
    )


def _optional_float(value: str | None) -> float | None:
    return None if value in (None, "") else float(value)


def latest_per_sensor(
    readings: list[LoggedReading],
) -> dict[tuple[str, int], LoggedReading]:
    latest: dict[tuple[str, int], LoggedReading] = {}
    for reading in readings:
        latest[reading.sensor_key] = reading
    return latest
