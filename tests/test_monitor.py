import csv
import json

import pytest

from backend.monitor import (
    CsvLog,
    RollingAverageDetector,
    SensorReading,
    parse_reading,
)


def reading(temp_c: float, channel: int = 0) -> SensorReading:
    return SensorReading("bench-unit", channel, temp_c, 25.0, None)


def test_detector_flags_jump_against_previous_samples() -> None:
    detector = RollingAverageDetector(
        window_size=4,
        minimum_samples=3,
        deviation_limit_c=5.0,
        critical_limit_c=100.0,
    )
    for value in [30.0, 31.0, 29.0]:
        assert detector.assess(reading(value)).abnormal is False

    result = detector.assess(reading(40.0))

    assert result.baseline_c == pytest.approx(30.0)
    assert result.deviation_c == pytest.approx(10.0)
    assert result.abnormal is True


def test_detector_keeps_channel_baselines_separate() -> None:
    detector = RollingAverageDetector(minimum_samples=2)
    detector.assess(reading(30.0, channel=0))
    detector.assess(reading(32.0, channel=0))

    first_other_channel = detector.assess(reading(60.0, channel=1))

    assert first_other_channel.baseline_c is None
    assert first_other_channel.abnormal is False


def test_parse_reading_validates_payload() -> None:
    payload = json.dumps(
        {
            "device_id": "panel-a",
            "channel": 2,
            "temp_c": 42.3,
            "ambient_c": 28.1,
            "sequence": 11,
            "valid": True,
        }
    )

    result = parse_reading(payload)

    assert result.device_id == "panel-a"
    assert result.channel == 2
    assert result.temp_c == pytest.approx(42.3)


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b"[]",
        b'{"device_id":"x","channel":9,"temp_c":20}',
        b'{"device_id":"x","channel":0,"temp_c":"nan"}',
        b'{"device_id":"x","channel":0,"temp_c":20,"valid":false}',
    ],
)
def test_parse_reading_rejects_bad_messages(payload: bytes) -> None:
    with pytest.raises(ValueError):
        parse_reading(payload)


def test_csv_log_writes_header_once(tmp_path) -> None:
    detector = RollingAverageDetector(minimum_samples=2)
    path = tmp_path / "logs" / "temperature.csv"
    log = CsvLog(path)

    log.append(detector.assess(reading(30.0)))
    log.append(detector.assess(reading(31.0)))

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["device_id"] == "bench-unit"
    assert rows[1]["temp_c"] == "31.00"
