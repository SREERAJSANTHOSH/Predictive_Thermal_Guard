import math

import pytest

from thermal_symmetry_guard import (
    MIN_RISE_K,
    GroupMode,
    Reading,
    SymmetryGroup,
    Verdict,
)
from thermal_symmetry_guard.scenarios import Point, Rig, drive_row, three_phase_panel

COMMISSION = 120


def commission(group, rig, drive_k=20.0, cycles=COMMISSION):
    rig.settle(drive_k)
    report = None
    for readings in rig.run(cycles, drive_k):
        report = group.update(readings)
    return report


def verdicts(report):
    return {c.point_id: c.verdict for c in report.channels}


def by_id(report, pid):
    return next(c for c in report.channels if c.point_id == pid)


class TestConstruction:
    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            SymmetryGroup("g", [])

    def test_rejects_duplicates(self):
        with pytest.raises(ValueError):
            SymmetryGroup("g", ["A", "A"])

    def test_rejects_unknown_point(self):
        g = SymmetryGroup("g", ["A", "B", "C"])
        with pytest.raises(KeyError):
            g.update([Reading("Z", 40.0, 25.0, 1.0)])


class TestEmissivityInvariance:
    """The central claim: verdicts must not depend on emissivity."""

    def test_wildly_different_gains_all_read_symmetric(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        report = commission(g, rig)
        assert all(v is Verdict.SYMMETRIC for v in verdicts(report).values())

    def test_learned_offset_tracks_the_gain_ratio(self):
        """The offset should equal log(gain) up to a shared constant."""
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        off = {p: g.channels[p].offset for p in rig.point_ids}
        expected = {p.point_id: math.log(p.gain) for p in rig.points}
        d_measured = off["L1"] - off["L2"]
        d_expected = expected["L1"] - expected["L2"]
        assert d_measured == pytest.approx(d_expected, abs=0.05)

    def test_identical_verdicts_under_a_global_gain_change(self):
        """Repainting every surface must not change any verdict."""
        out = []
        for scale in (0.5, 1.0):
            rig = three_phase_panel()
            for p in rig.points:
                p.gain *= scale
            g = SymmetryGroup("panel", rig.point_ids)
            out.append(verdicts(commission(g, rig)))
        assert out[0] == out[1]


class TestCommonModeRejection:
    def test_large_shared_rise_is_not_a_fault(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        report = None
        for drive in range(20, 60):
            report = g.update(rig.sweep(float(drive)))
        assert all(
            v in (Verdict.COMMON_MODE_RISE, Verdict.SYMMETRIC)
            for v in verdicts(report).values()
        )
        assert report.common_mode_rising

    def test_ambient_swing_is_rejected(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        report = None
        for i in range(40):
            report = g.update(rig.sweep(20.0, ambient_c=25.0 + i * 0.4))
        assert not any(
            v in (Verdict.ASYMMETRIC_HOT, Verdict.ASYMMETRIC_COLD)
            for v in verdicts(report).values()
        )


class TestFaultDetection:
    def test_single_phase_hot_spot_is_caught(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        rig.points[0].fault_k = 8.0
        report = None
        for readings in rig.run(40, 20.0):
            report = g.update(readings)
        assert verdicts(report)["L1"] is Verdict.ASYMMETRIC_HOT
        assert verdicts(report)["L2"] is not Verdict.ASYMMETRIC_HOT
        assert by_id(report, "L1").robust_z > 3.5

    def test_fault_caught_on_the_low_emissivity_point(self):
        """The hardest case: a fault on the surface that radiates least."""
        rig = three_phase_panel()
        assert rig.points[0].gain == 0.55
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        rig.points[0].fault_k = 6.0
        report = None
        for readings in rig.run(40, 20.0):
            report = g.update(readings)
        assert verdicts(report)["L1"] is Verdict.ASYMMETRIC_HOT

    def test_fault_during_a_load_ramp_still_caught(self):
        """A fault hidden inside a big common-mode rise."""
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        rig.points[2].fault_k = 8.0
        report = None
        for i in range(50):
            report = g.update(rig.sweep(20.0 + i * 0.7))
        assert verdicts(report)["L3"] is Verdict.ASYMMETRIC_HOT

    def test_cold_point_flagged(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig, drive_k=30.0)
        rig.points[1].fault_k = -12.0
        report = None
        for readings in rig.run(40, 30.0):
            report = g.update(readings)
        assert verdicts(report)["L2"] is Verdict.ASYMMETRIC_COLD

    def test_slow_drift_caught_by_cusum_below_z_threshold(self):
        """The signal a plain threshold detector always misses."""
        rig = drive_row(6)
        g = SymmetryGroup("row", rig.point_ids, z_warn=3.5)
        commission(g, rig, drive_k=25.0)
        report = None
        for i in range(120):
            rig.points[0].fault_k = 0.02 * i
            report = g.update(rig.sweep(25.0))
        ch = by_id(report, rig.point_ids[0])
        assert ch.verdict is Verdict.ASYMMETRIC_HOT
        assert abs(ch.cusum) > 5.0

    def test_no_false_alarm_over_a_long_quiet_run(self):
        rig = drive_row(6, seed=11)
        g = SymmetryGroup("row", rig.point_ids)
        commission(g, rig, drive_k=25.0)
        alarms = 0
        for readings in rig.run(600, 25.0):
            rep = g.update(readings)
            alarms += sum(
                c.verdict in (Verdict.ASYMMETRIC_HOT, Verdict.ASYMMETRIC_COLD)
                for c in rep.channels
            )
        assert alarms == 0


class TestFaultCannotBeLearned:
    def test_sustained_fault_does_not_become_the_new_normal(self):
        """A slowly-adapting baseline would silently absorb a real fault."""
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        rig.points[0].fault_k = 8.0
        report = None
        for readings in rig.run(400, 20.0):
            report = g.update(readings)
        assert verdicts(report)["L1"] is Verdict.ASYMMETRIC_HOT


class TestNearAmbient:
    def test_below_floor_reports_warming_up(self):
        g = SymmetryGroup("g", ["A", "B", "C"])
        rep = g.update([Reading(p, 25.2, 25.0, 1.0) for p in ("A", "B", "C")])
        assert all(c.verdict is Verdict.WARMING_UP for c in rep.channels)

    def test_no_log_of_negative_rise(self):
        g = SymmetryGroup("g", ["A", "B", "C"])
        rep = g.update([Reading(p, 20.0, 25.0, 1.0) for p in ("A", "B", "C")])
        assert all(math.isfinite(c.asymmetry) for c in rep.channels)

    def test_floor_is_respected_exactly(self):
        g = SymmetryGroup("g", ["A", "B", "C"])
        rep = g.update(
            [Reading(p, 25.0 + MIN_RISE_K - 0.01, 25.0, 1.0) for p in ("A", "B", "C")]
        )
        assert all(c.verdict is Verdict.WARMING_UP for c in rep.channels)


class TestDegradedModes:
    def test_two_points_falls_back_to_self_history(self):
        rig = Rig(points=[Point("A", 0.8), Point("B", 0.6)], seed=3)
        g = SymmetryGroup("pair", rig.point_ids)
        rep = commission(g, rig)
        assert rep.mode is GroupMode.SELF_HISTORY

    def test_missing_sensor_flagged_after_three_sweeps(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        rep = None
        for _ in range(4):
            rep = g.update([r for r in rig.sweep(20.0) if r.point_id != "L2"])
        assert verdicts(rep)["L2"] is Verdict.SENSOR_SUSPECT

    def test_quarantined_point_leaves_the_median(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        g.quarantine("L1")
        rep = g.update(rig.sweep(20.0))
        assert rep.mode is GroupMode.SELF_HISTORY
        g.release("L1")
        rep = g.update(rig.sweep(20.0))
        assert rep.mode is GroupMode.PEER_MEDIAN

    def test_median_survives_one_wild_sensor(self):
        """Three points, one reading nonsense: the median must not follow it."""
        rig = drive_row(6)
        g = SymmetryGroup("row", rig.point_ids)
        commission(g, rig, drive_k=25.0)
        readings = rig.sweep(25.0)
        poisoned = [
            Reading(r.point_id, 400.0 if i == 0 else r.temp_c, r.ambient_c, r.t_s)
            for i, r in enumerate(readings)
        ]
        rep = g.update(poisoned)
        others = [c for c in rep.channels if c.point_id != rig.point_ids[0]]
        assert all(
            c.verdict not in (Verdict.ASYMMETRIC_HOT, Verdict.ASYMMETRIC_COLD)
            for c in others
        )
        assert by_id(rep, rig.point_ids[0]).verdict is Verdict.ASYMMETRIC_HOT


class TestReportShape:
    def test_worst_channel_is_the_faulted_one(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        commission(g, rig)
        rig.points[0].fault_k = 9.0
        rep = None
        for readings in rig.run(40, 20.0):
            rep = g.update(readings)
        assert rep.worst.point_id == "L1"

    def test_every_channel_reported_every_cycle(self):
        rig = drive_row(6)
        g = SymmetryGroup("row", rig.point_ids)
        rep = commission(g, rig, drive_k=25.0, cycles=10)
        assert len(rep.channels) == 6

    def test_all_numbers_finite(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        rep = commission(g, rig)
        for c in rep.channels:
            assert math.isfinite(c.asymmetry)
            assert math.isfinite(c.robust_z)
            assert math.isfinite(c.cusum)

    def test_detail_is_always_actionable_text(self):
        rig = three_phase_panel()
        g = SymmetryGroup("panel", rig.point_ids)
        rep = commission(g, rig)
        assert all(c.detail for c in rep.channels)
