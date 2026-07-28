"""Runnable narrative demo: ``python -m thermal_symmetry_guard.demo``.

Walks a three-phase panel through commissioning, a load ramp, and a genuine
single-phase fault, printing what the engine concludes at each stage.
"""

from __future__ import annotations

from .scenarios import three_phase_panel
from .symmetry import SymmetryGroup
from .types import GroupReport, Verdict

_MARK = {
    Verdict.SYMMETRIC: "  ok  ",
    Verdict.COMMON_MODE_RISE: " load ",
    Verdict.WARMING_UP: " wait ",
    Verdict.ASYMMETRIC_HOT: " HOT  ",
    Verdict.ASYMMETRIC_COLD: " COLD ",
    Verdict.TAU_SHIFT: " TAU  ",
    Verdict.SENSOR_SUSPECT: " ???  ",
}


def show(title: str, report: GroupReport) -> None:
    print(f"\n{title}")
    print(f"  mode={report.mode.value}  common_mode={report.common_mode:+.3f}")
    for c in sorted(report.channels, key=lambda c: c.point_id):
        print(
            f"  [{_MARK[c.verdict]}] {c.point_id:<5} "
            f"apparent {c.temp_c:5.1f} C  rise {c.rise_k:5.1f} K  "
            f"z={c.robust_z:+6.2f}  cusum={c.cusum:+7.1f}"
        )
        print(f"          {c.detail}")


def main() -> None:
    rig = three_phase_panel()
    group = SymmetryGroup("main-panel", rig.point_ids)

    print("Thermal Symmetry Guard — three-phase panel")
    print("True emissivities (never known to the engine):")
    for p in rig.points:
        print(f"  {p.point_id}: {p.gain:.2f}")

    rig.settle(20.0)
    report = None
    for readings in rig.run(120, 20.0):
        report = group.update(readings)
    show("1. Commissioned, steady load — three very different surfaces", report)

    for i in range(40):
        report = group.update(rig.sweep(20.0 + i * 0.9))
    show("2. Load ramp: every lug climbs 35 K together", report)

    rig.points[0].fault_k = 7.0
    for _ in range(40):
        report = group.update(rig.sweep(56.0))
    show("3. L1 develops a loose lug (+7 K on that phase only)", report)

    worst = report.worst
    print(f"\nVerdict: {worst.point_id} -> {worst.verdict.value}")
    print("No emissivity was configured, and no contact probe was ever attached.")


if __name__ == "__main__":
    main()
