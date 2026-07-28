from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any

import paho.mqtt.client as mqtt


@dataclass(frozen=True)
class SensorReading:
    device_id: str
    channel: int
    temp_c: float
    ambient_c: float | None
    sequence: int | None


@dataclass(frozen=True)
class Assessment:
    reading: SensorReading
    baseline_c: float | None
    deviation_c: float | None
    abnormal: bool
    reason: str


class RollingAverageDetector:
    """Compare each sample with earlier samples from the same sensor."""

    def __init__(
        self,
        window_size: int = 20,
        minimum_samples: int = 8,
        deviation_limit_c: float = 8.0,
        critical_limit_c: float = 85.0,
    ) -> None:
        if window_size < 2:
            raise ValueError("window_size must be at least 2")
        if not 1 <= minimum_samples <= window_size:
            raise ValueError("minimum_samples must be within the window")
        if deviation_limit_c <= 0:
            raise ValueError("deviation_limit_c must be positive")

        self.minimum_samples = minimum_samples
        self.deviation_limit_c = deviation_limit_c
        self.critical_limit_c = critical_limit_c
        self._history: dict[tuple[str, int], deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    def assess(self, reading: SensorReading) -> Assessment:
        key = (reading.device_id, reading.channel)
        history = self._history[key]
        baseline = fmean(history) if history else None
        deviation = (
            reading.temp_c - baseline if baseline is not None else None
        )

        abnormal = False
        reason = "warming up baseline"
        if reading.temp_c >= self.critical_limit_c:
            abnormal = True
            reason = f"temperature at or above {self.critical_limit_c:.1f} C"
        elif len(history) >= self.minimum_samples:
            abnormal = abs(deviation or 0.0) >= self.deviation_limit_c
            reason = (
                f"deviation at or above {self.deviation_limit_c:.1f} C"
                if abnormal
                else "within rolling baseline"
            )

        # The current value is appended after the comparison so a sudden jump
        # cannot pull its own baseline towards the fault.
        history.append(reading.temp_c)
        return Assessment(reading, baseline, deviation, abnormal, reason)


class CsvLog:
    fieldnames = [
        "timestamp_utc",
        "device_id",
        "channel",
        "temp_c",
        "ambient_c",
        "baseline_c",
        "deviation_c",
        "abnormal",
        "reason",
        "sequence",
    ]

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, assessment: Assessment) -> None:
        is_new_file = not self.path.exists() or self.path.stat().st_size == 0
        reading = assessment.reading
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "device_id": reading.device_id,
            "channel": reading.channel,
            "temp_c": f"{reading.temp_c:.2f}",
            "ambient_c": _format_optional(reading.ambient_c),
            "baseline_c": _format_optional(assessment.baseline_c),
            "deviation_c": _format_optional(assessment.deviation_c),
            "abnormal": str(assessment.abnormal).lower(),
            "reason": assessment.reason,
            "sequence": "" if reading.sequence is None else reading.sequence,
        }

        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
            if is_new_file:
                writer.writeheader()
            writer.writerow(row)


def _format_optional(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def parse_reading(payload: bytes | str) -> SensorReading:
    try:
        raw: Any = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("payload is not valid JSON") from exc

    if not isinstance(raw, dict):
        raise ValueError("payload must be a JSON object")
    if raw.get("valid", True) is not True:
        raise ValueError("sensor marked the reading invalid")

    device_id = str(raw.get("device_id", "")).strip()
    if not device_id:
        raise ValueError("device_id is required")

    channel = raw.get("channel")
    if isinstance(channel, bool) or not isinstance(channel, int):
        raise ValueError("channel must be an integer")
    if not 0 <= channel <= 7:
        raise ValueError("channel must be between 0 and 7")

    temp_c = _finite_float(raw.get("temp_c"), "temp_c")
    if not -70.0 <= temp_c <= 380.0:
        raise ValueError("temp_c is outside the MLX90614 measurement range")

    ambient_raw = raw.get("ambient_c")
    ambient_c = (
        None
        if ambient_raw is None
        else _finite_float(ambient_raw, "ambient_c")
    )

    sequence_raw = raw.get("sequence")
    sequence = (
        sequence_raw
        if isinstance(sequence_raw, int) and not isinstance(sequence_raw, bool)
        else None
    )
    return SensorReading(device_id, channel, temp_c, ambient_c, sequence)


def _finite_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


class Monitor:
    def __init__(
        self,
        broker: str,
        port: int,
        topic: str,
        detector: RollingAverageDetector,
        csv_log: CsvLog,
    ) -> None:
        self.broker = broker
        self.port = port
        self.topic = topic
        self.detector = detector
        self.csv_log = csv_log
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="thermal-fault-guard-monitor",
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del userdata, flags, properties
        if reason_code.is_failure:
            print(f"MQTT connection failed: {reason_code}")
            return
        client.subscribe(self.topic)
        print(f"subscribed to {self.topic}")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata
        try:
            assessment = self.detector.assess(parse_reading(message.payload))
        except ValueError as exc:
            print(f"ignored {message.topic}: {exc}")
            return

        self.csv_log.append(assessment)
        reading = assessment.reading
        state = "FAULT" if assessment.abnormal else "normal"
        print(
            f"{reading.device_id} channel {reading.channel}: "
            f"{reading.temp_c:.2f} C [{state}]"
        )

    def run(self) -> None:
        print(f"connecting to MQTT broker {self.broker}:{self.port}")
        self.client.connect(self.broker, self.port, keepalive=60)
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("\nstopping monitor")
        finally:
            self.client.disconnect()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Log ESP32 temperature readings and flag deviations."
    )
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument(
        "--topic", default="thermal-fault-guard/+/temperature"
    )
    parser.add_argument("--csv", type=Path, default=Path("temperature_log.csv"))
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--minimum-samples", type=int, default=8)
    parser.add_argument("--deviation", type=float, default=8.0)
    parser.add_argument("--critical", type=float, default=85.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    detector = RollingAverageDetector(
        window_size=args.window,
        minimum_samples=args.minimum_samples,
        deviation_limit_c=args.deviation,
        critical_limit_c=args.critical,
    )
    Monitor(
        broker=args.broker,
        port=args.port,
        topic=args.topic,
        detector=detector,
        csv_log=CsvLog(args.csv),
    ).run()


if __name__ == "__main__":
    main()

