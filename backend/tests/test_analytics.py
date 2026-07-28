import pytest

from thermal_guard.analytics import ThermalAnalyzer
from thermal_guard.config import Settings
from thermal_guard.models import SensorReading


def test_frame_summary_locates_hotspot() -> None:
    summary = ThermalAnalyzer.summarize_frame(3, 2, [20, 21, 22, 23, 51, 25])
    assert summary.maximum_c == 51
    assert summary.minimum_c == 20
    assert (summary.hotspot_x, summary.hotspot_y) == (1, 1)


def test_adaptive_detector_catches_statistical_jump() -> None:
    analyzer = ThermalAnalyzer(
        Settings(
            database_path=":memory:",
            absolute_warning_c=200,
            anomaly_z_warning=2.5,
            baseline_alpha=0.05,
        )
    )
    for index in range(12):
        result = analyzer.evaluate(
            SensorReading(
                device_id="panel",
                sensor_id="L1",
                temperature_c=40 + (index % 2) * 0.1,
            )
        )
        assert result is None
    alert = analyzer.evaluate(
        SensorReading(device_id="panel", sensor_id="L1", temperature_c=48)
    )
    assert alert is not None
    assert alert.z_score >= 2.5
    assert alert.cause == "adaptive"
    assert alert.threshold_c < alert.temperature_c


def test_frame_model_rejects_invalid_pixel_count() -> None:
    from pydantic import ValidationError

    from thermal_guard.models import ThermalFrame

    with pytest.raises(ValidationError):
        ThermalFrame(device_id="cam", width=2, height=2, pixels_c=[1, 2, 3])
