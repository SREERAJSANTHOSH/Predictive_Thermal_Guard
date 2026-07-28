from pathlib import Path

from desktop.csv_source import latest_per_sensor, load_readings


def test_load_readings_and_latest_per_sensor(tmp_path: Path) -> None:
    path = tmp_path / "temperature.csv"
    path.write_text(
        "timestamp_utc,device_id,channel,temp_c,ambient_c,baseline_c,"
        "deviation_c,abnormal,reason,sequence\n"
        "2026-01-01T10:00:00+00:00,panel-a,0,30.00,25.00,,,false,"
        "warming up baseline,1\n"
        "2026-01-01T10:00:01+00:00,panel-a,0,31.00,25.00,30.00,"
        "1.00,false,within rolling baseline,2\n"
        "2026-01-01T10:00:01+00:00,panel-a,1,40.00,25.00,,,false,"
        "warming up baseline,3\n",
        encoding="utf-8",
    )

    readings = load_readings(path)
    latest = latest_per_sensor(readings)

    assert len(readings) == 3
    assert latest[("panel-a", 0)].temp_c == 31.0
    assert latest[("panel-a", 1)].temp_c == 40.0


def test_load_readings_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_readings(tmp_path / "missing.csv") == []
