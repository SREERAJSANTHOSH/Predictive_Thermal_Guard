import math

from research.analyze_calibration import summarize


def test_summarize_known_errors() -> None:
    metrics = summarize([1.0, -1.0, 2.0])

    assert metrics["count"] == 3
    assert math.isclose(float(metrics["bias_c"]), 2 / 3)
    assert math.isclose(float(metrics["mae_c"]), 4 / 3)
    assert math.isclose(float(metrics["rmse_c"]), math.sqrt(2))
    assert metrics["maximum_absolute_error_c"] == 2.0
