import math

import pytest

from thermal_symmetry_guard.robust import (
    Cusum,
    RobustBaseline,
    TrendFilter,
    mad,
    median,
)


class TestMedian:
    def test_odd_and_even(self):
        assert median([3, 1, 2]) == 2
        assert median([4, 1, 3, 2]) == 2.5

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            median([])

    def test_resists_outlier(self):
        assert median([10, 11, 12, 9, 1000]) == 11


class TestMad:
    def test_known_value(self):
        assert mad([1, 2, 3, 4, 5]) == 1.0

    def test_zero_for_constant(self):
        assert mad([7.0] * 9) == 0.0


class TestRobustBaseline:
    def test_rejects_bad_window(self):
        with pytest.raises(ValueError):
            RobustBaseline(window=2)
        with pytest.raises(ValueError):
            RobustBaseline(sigma_floor=0.0)

    def test_sigma_floor_prevents_infinite_z(self):
        """The bug that makes naive z-score detectors unusable on quantised data."""
        b = RobustBaseline(window=32, sigma_floor=0.05)
        b.extend([20.0] * 32)
        assert b.sigma == 0.05
        z = b.z(20.1)
        assert math.isfinite(z)
        assert z == pytest.approx(2.0)

    def test_not_ready_when_empty(self):
        assert not RobustBaseline(window=64).ready

    def test_ignores_nan(self):
        b = RobustBaseline(window=16)
        b.extend([1.0, float("nan"), 1.0, float("inf")])
        assert b.count == 2

    def test_z_of_nan_is_zero(self):
        b = RobustBaseline(window=16)
        b.extend([1.0] * 16)
        assert b.z(float("nan")) == 0.0

    def test_single_outlier_barely_moves_center(self):
        b = RobustBaseline(window=64, sigma_floor=0.01)
        b.extend([5.0] * 40)
        b.feed(500.0)
        assert b.center == pytest.approx(5.0)

    def test_window_evicts(self):
        b = RobustBaseline(window=10)
        b.extend(range(50))
        assert b.count == 10
        assert b.center == pytest.approx(44.5)


class TestCusum:
    def test_ignores_noise_below_slack(self):
        c = Cusum(slack=0.5, limit=5.0)
        for _ in range(200):
            c.feed(0.3)
        assert not c.tripped

    def test_detects_sustained_small_shift(self):
        """A 1-sigma bias never trips a 3.5-sigma threshold but must trip CUSUM."""
        c = Cusum(slack=0.5, limit=5.0)
        tripped_at = None
        for i in range(1, 100):
            c.feed(1.0)
            if c.tripped:
                tripped_at = i
                break
        assert tripped_at is not None
        assert tripped_at <= 12

    def test_detects_negative_drift(self):
        c = Cusum()
        for _ in range(30):
            c.feed(-1.0)
        assert c.tripped
        assert c.value < 0

    def test_reset_clears(self):
        c = Cusum()
        for _ in range(30):
            c.feed(2.0)
        assert c.tripped
        c.reset()
        assert not c.tripped
        assert c.value == 0.0

    def test_nan_treated_as_zero(self):
        c = Cusum()
        c.feed(float("nan"))
        assert c.value == 0.0

    def test_rejects_bad_params(self):
        with pytest.raises(ValueError):
            Cusum(slack=-1)
        with pytest.raises(ValueError):
            Cusum(limit=0)


class TestTrendFilter:
    def test_no_slope_before_warmup(self):
        f = TrendFilter(warmup=4)
        f.feed(10.0, 0.0)
        f.feed(11.0, 1.0)
        assert f.slope_per_s == 0.0

    def test_tracks_linear_ramp(self):
        f = TrendFilter(alpha=0.5, beta=0.3, warmup=4)
        for i in range(60):
            f.feed(20.0 + 0.1 * i, float(i))
        assert f.slope_per_s == pytest.approx(0.1, abs=0.02)

    def test_slope_negative_when_cooling(self):
        f = TrendFilter(alpha=0.5, beta=0.3)
        for i in range(60):
            f.feed(80.0 - 0.2 * i, float(i))
        assert f.slope_per_s < 0

    def test_handles_duplicate_timestamps(self):
        f = TrendFilter()
        f.feed(1.0, 5.0)
        f.feed(2.0, 5.0)
        assert math.isfinite(f.slope)

    def test_rejects_bad_params(self):
        with pytest.raises(ValueError):
            TrendFilter(alpha=0.0)
        with pytest.raises(ValueError):
            TrendFilter(beta=2.0)
