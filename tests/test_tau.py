import math

import pytest

from thermal_symmetry_guard import Reading, SymmetryGroup, Verdict
from thermal_symmetry_guard.symmetry import TauEstimator, _ols_slope


def cooling_curve(tau_s, rise0=40.0, gain=0.7, dt=4.0, n=40, t0=0.0):
    """An ideal exponential cooldown seen through an unknown emissivity gain."""
    out = []
    for i in range(n):
        t = t0 + i * dt
        rise = rise0 * math.exp(-(i * dt) / tau_s)
        out.append((t, math.log(gain * rise)))
    return out


class TestOlsSlope:
    def test_exact_line(self):
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [1.0, 3.0, 5.0, 7.0]
        assert _ols_slope(xs, ys) == pytest.approx(2.0)

    def test_no_spread_returns_none(self):
        assert _ols_slope([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None

    def test_too_short_returns_none(self):
        assert _ols_slope([1.0], [1.0]) is None


class TestTauEstimator:
    def test_recovers_known_tau(self):
        est = TauEstimator()
        tau = None
        for t, y in cooling_curve(200.0):
            tau = est.feed(t, y, cooling=True) or tau
        assert tau == pytest.approx(200.0, rel=0.02)

    def test_tau_is_independent_of_emissivity(self):
        """The whole reason tau is trustworthy: gain shifts intercept, not slope."""
        taus = []
        for gain in (0.2, 0.55, 0.95):
            est = TauEstimator()
            for t, y in cooling_curve(180.0, gain=gain):
                est.feed(t, y, cooling=True)
            taus.append(est.tau_s)
        assert taus[0] == pytest.approx(180.0, rel=0.02)
        assert taus[0] == pytest.approx(taus[2], rel=0.01)

    def test_rejects_too_few_samples(self):
        est = TauEstimator(min_samples=8)
        for t, y in cooling_curve(200.0, n=4):
            est.feed(t, y, cooling=True)
        assert est.tau_s is None

    def test_rejects_too_short_a_span(self):
        est = TauEstimator(min_span_s=1000.0)
        for t, y in cooling_curve(200.0, n=20):
            est.feed(t, y, cooling=True)
        assert est.tau_s is None

    def test_rejects_insufficient_decay(self):
        """A nearly flat 'cooldown' carries no tau information."""
        est = TauEstimator(min_decay=0.5)
        for t, y in cooling_curve(100000.0, n=30):
            est.feed(t, y, cooling=True)
        assert est.tau_s is None

    def test_rejects_a_warming_segment(self):
        est = TauEstimator()
        for i in range(30):
            est.feed(i * 4.0, math.log(5.0 + i), cooling=True)
        assert est.tau_s is None

    def test_segment_resets_when_cooling_stops(self):
        est = TauEstimator()
        for t, y in cooling_curve(200.0, n=20):
            est.feed(t, y, cooling=True)
        est.feed(500.0, None, cooling=False)
        assert est.feed(504.0, 1.0, cooling=True) is None

    def test_time_gap_starts_a_new_episode(self):
        """Two cooldowns a week apart must not be fitted as one line."""
        est = TauEstimator()
        for t, y in cooling_curve(200.0, n=20):
            est.feed(t, y, cooling=True)
        assert est.feed(600000.0, 1.0, cooling=True) is None


class TestTauShiftVerdict:
    def _run_cooldown(self, group, pids, tau_map, t0, rise0=40.0, gains=None):
        gains = gains or dict.fromkeys(pids, 0.7)
        rep = None
        for i in range(45):
            t = t0 + i * 4.0
            readings = []
            for p in pids:
                rise = rise0 * math.exp(-(i * 4.0) / tau_map[p])
                readings.append(Reading(p, 25.0 + gains[p] * rise, 25.0, t))
            rep = group.update(readings)
        return rep

    def test_tau_shift_flagged_when_thermal_path_degrades(self):
        pids = ["A", "B", "C"]
        g = SymmetryGroup("rack", pids, tau_tolerance=0.25)
        baseline = dict.fromkeys(pids, 200.0)
        self._run_cooldown(g, pids, baseline, t0=0.0)
        for p in pids:
            g.channels[p].baseline_tau_s = g.channels[p].tau_estimator.tau_s
        assert g.channels["A"].baseline_tau_s == pytest.approx(200.0, rel=0.05)

        degraded = {"A": 320.0, "B": 200.0, "C": 200.0}
        rep = self._run_cooldown(g, pids, degraded, t0=5000.0)
        ch = next(c for c in rep.channels if c.point_id == "A")
        assert ch.tau_ratio == pytest.approx(1.6, rel=0.15)
        assert ch.verdict is Verdict.TAU_SHIFT
        assert "slower" in ch.detail

    def test_tau_within_tolerance_is_not_flagged(self):
        pids = ["A", "B", "C"]
        g = SymmetryGroup("rack", pids, tau_tolerance=0.25)
        self._run_cooldown(g, pids, dict.fromkeys(pids, 200.0), t0=0.0)
        for p in pids:
            g.channels[p].baseline_tau_s = g.channels[p].tau_estimator.tau_s
        rep = self._run_cooldown(g, pids, dict.fromkeys(pids, 210.0), t0=5000.0)
        assert all(c.verdict is not Verdict.TAU_SHIFT for c in rep.channels)

    def test_tau_shift_survives_a_repaint(self):
        """Change every gain between the two cooldowns; tau must be unaffected."""
        pids = ["A", "B", "C"]
        g = SymmetryGroup("rack", pids, tau_tolerance=0.25)
        self._run_cooldown(
            g, pids, dict.fromkeys(pids, 200.0), t0=0.0,
            gains=dict.fromkeys(pids, 0.9),
        )
        for p in pids:
            g.channels[p].baseline_tau_s = g.channels[p].tau_estimator.tau_s
        rep = self._run_cooldown(
            g, pids, dict.fromkeys(pids, 200.0), t0=5000.0,
            gains=dict.fromkeys(pids, 0.35),
        )
        assert all(c.verdict is not Verdict.TAU_SHIFT for c in rep.channels)
