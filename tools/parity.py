"""C <-> Python numerical parity harness.

The embedded core in ``firmware/src/symmetry.c`` is a hand port of the Python
reference. A hand port that is merely *reviewed* is a hand port that is wrong,
so this harness compiles the C, drives both implementations over byte-identical
input, and asserts the outputs agree.

Tolerances are tight but not zero: the C works in ``float`` while Python uses
``double``, so a few ULP of divergence per sample is expected and accumulates
slowly through the rolling windows. Verdicts, being discrete, must match
exactly -- that is the property that actually matters in the field.

Run directly (``python tools/parity.py``) or via pytest (``tests/test_parity.py``).
"""

from __future__ import annotations

import ctypes
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "firmware" / "src" / "symmetry.c"
INC = ROOT / "firmware" / "include"

MAX_POINTS = 8

# Verdict enum ordering, mirrored from symmetry.h. Kept as a plain tuple so a
# reordering of the C enum shows up as a parity failure rather than silently
# remapping.
C_VERDICTS = (
    "warming_up",
    "symmetric",
    "common_mode_rise",
    "asymmetric_hot",
    "asymmetric_cold",
    "tau_shift",
    "sensor_suspect",
)

TOL_ASYM = 2e-4
TOL_Z = 5e-2
TOL_TAU_RATIO = 5e-3


class CResult(ctypes.Structure):
    _fields_ = [
        ("verdict", ctypes.c_int),
        ("temp_c", ctypes.c_float),
        ("rise_k", ctypes.c_float),
        ("asymmetry", ctypes.c_float),
        ("z", ctypes.c_float),
        ("cusum", ctypes.c_float),
        ("tau_s", ctypes.c_float),
        ("tau_ratio", ctypes.c_float),
    ]


@dataclass
class Divergence:
    cycle: int
    point_id: str
    field: str
    c_value: object
    py_value: object

    def __str__(self) -> str:
        return (
            f"cycle {self.cycle:>4} {self.point_id:<6} {self.field:<10} "
            f"C={self.c_value!r:<22} Py={self.py_value!r}"
        )


def _stub_headers(directory: Path) -> None:
    """Freestanding libc subset.

    The C core deliberately uses only a handful of libc entry points, so a full
    toolchain is not required to exercise it. This keeps the harness runnable
    anywhere Python and a C compiler exist.
    """
    (directory / "math.h").write_text(
        "#pragma once\n"
        '#define NAN (__builtin_nanf(""))\n'
        "#define isfinite(x) __builtin_isfinite(x)\n"
        "float fabsf(float); float fmaxf(float,float);\n"
        "float fminf(float,float); float logf(float);\n"
    )
    (directory / "string.h").write_text(
        "#pragma once\n"
        "typedef __SIZE_TYPE__ size_t;\n"
        "void *memcpy(void*,const void*,size_t);\n"
        "void *memset(void*,int,size_t);\n"
        "void *memmove(void*,const void*,size_t);\n"
        "char *strncpy(char*,const char*,size_t);\n"
    )
    (directory / "stdint.h").write_text(
        "#pragma once\n"
        "typedef unsigned char uint8_t; typedef signed char int8_t;\n"
        "typedef unsigned short uint16_t;\n"
        "typedef int int32_t; typedef unsigned int uint32_t;\n"
    )
    (directory / "stdbool.h").write_text(
        "#pragma once\n#define bool _Bool\n#define true 1\n#define false 0\n"
    )


def build_library(out_dir: Path | None = None) -> ctypes.CDLL:
    """Compile the firmware core into a loadable shared object."""
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        raise RuntimeError("no C compiler on PATH")

    tmp = out_dir or Path(tempfile.mkdtemp(prefix="tsg-parity-"))
    stub = tmp / "stub"
    stub.mkdir(parents=True, exist_ok=True)
    _stub_headers(stub)

    so = tmp / "libtsg.so"
    cmd = [
        cc, "-std=c11", "-O2", "-Wall", "-Wextra",
        "-shared", "-fPIC", "-nostdinc", "-nostdlib",
        f"-I{stub}", f"-I{INC}",
        str(SRC), "-o", str(so),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"C build failed:\n{proc.stderr}")
    if proc.stderr.strip():
        raise RuntimeError(f"C build produced warnings:\n{proc.stderr}")

    lib = ctypes.CDLL(str(so))
    lib.tsg_group_init.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.tsg_group_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.tsg_group_add.restype = ctypes.c_bool
    lib.tsg_group_update.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_bool),
        ctypes.c_float,
        ctypes.c_float,
        ctypes.POINTER(CResult),
    ]
    lib.tsg_verdict_name.argtypes = [ctypes.c_int]
    lib.tsg_verdict_name.restype = ctypes.c_char_p
    return lib


class CGroup:
    """ctypes wrapper around the embedded core."""

    #  Generous fixed buffer: the exact struct layout is opaque to Python, so
    #  the harness only needs it to be at least as large as the real thing.
    _BUF_BYTES = 1 << 16

    def __init__(self, lib: ctypes.CDLL, point_ids: list[str], z_warn: float = 3.5):
        if len(point_ids) > MAX_POINTS:
            raise ValueError(f"C core supports at most {MAX_POINTS} points")
        self.lib = lib
        self.point_ids = point_ids
        self._buf = ctypes.create_string_buffer(self._BUF_BYTES)
        self._ptr = ctypes.cast(self._buf, ctypes.c_void_p)
        lib.tsg_group_init(self._ptr, ctypes.c_float(z_warn))
        for pid in point_ids:
            if not lib.tsg_group_add(self._ptr, pid.encode()):
                raise RuntimeError(f"tsg_group_add rejected {pid}")

    def update(
        self, temps: dict[str, float], ambient_c: float, t_s: float
    ) -> dict[str, CResult]:
        n = len(self.point_ids)
        c_temps = (ctypes.c_float * MAX_POINTS)()
        c_present = (ctypes.c_bool * MAX_POINTS)()
        for i, pid in enumerate(self.point_ids):
            if pid in temps:
                c_temps[i] = temps[pid]
                c_present[i] = True
            else:
                c_present[i] = False
        out = (CResult * MAX_POINTS)()
        self.lib.tsg_group_update(
            self._ptr, c_temps, c_present,
            ctypes.c_float(ambient_c), ctypes.c_float(t_s), out,
        )
        return {pid: out[i] for i, pid in enumerate(self.point_ids[:n])}


def compare(
    point_ids: list[str],
    sweeps: list[tuple[dict[str, float], float, float]],
    *,
    z_warn: float = 3.5,
    lib: ctypes.CDLL | None = None,
) -> list[Divergence]:
    """Drive both implementations over identical input; return disagreements."""
    sys.path.insert(0, str(ROOT / "src"))
    from thermal_symmetry_guard import Reading, SymmetryGroup

    lib = lib or build_library()
    c_group = CGroup(lib, point_ids, z_warn=z_warn)
    py_group = SymmetryGroup("parity", point_ids, z_warn=z_warn)

    out: list[Divergence] = []
    for cycle, (temps, ambient_c, t_s) in enumerate(sweeps):
        c_res = c_group.update(temps, ambient_c, t_s)
        py_res = {
            r.point_id: r
            for r in py_group.update(
                [
                    Reading(pid, temps[pid], ambient_c, t_s)
                    for pid in point_ids
                    if pid in temps
                ]
            ).channels
        }

        for pid in point_ids:
            c = c_res[pid]
            p = py_res[pid]
            c_verdict = C_VERDICTS[c.verdict]

            if c_verdict != p.verdict.value:
                out.append(
                    Divergence(cycle, pid, "verdict", c_verdict, p.verdict.value)
                )

            if math.isfinite(p.asymmetry) and abs(c.asymmetry - p.asymmetry) > TOL_ASYM:
                out.append(
                    Divergence(cycle, pid, "asymmetry", c.asymmetry, p.asymmetry)
                )

            if math.isfinite(p.robust_z) and abs(c.z - p.robust_z) > TOL_Z:
                out.append(Divergence(cycle, pid, "z", c.z, p.robust_z))

            if (
                p.tau_ratio is not None
                and c.tau_ratio > 0.0
                and abs(c.tau_ratio - p.tau_ratio) > TOL_TAU_RATIO
            ):
                out.append(
                    Divergence(cycle, pid, "tau_ratio", c.tau_ratio, p.tau_ratio)
                )
    return out


# ------------------------------------------------------------------ scenarios


def _panel_sweeps() -> tuple[list[str], list[tuple[dict[str, float], float, float]]]:
    """Commission, ramp the load, then fault one phase."""
    sys.path.insert(0, str(ROOT / "src"))
    from thermal_symmetry_guard.scenarios import three_phase_panel

    rig = three_phase_panel()
    rig.settle(20.0)
    sweeps = []
    for _ in range(120):
        sweeps.append(_pack(rig.sweep(20.0)))
    for i in range(40):
        sweeps.append(_pack(rig.sweep(20.0 + i * 0.9)))
    rig.points[0].fault_k = 7.0
    for _ in range(40):
        sweeps.append(_pack(rig.sweep(56.0)))
    return rig.point_ids, sweeps


def _cooldown_sweeps() -> tuple[list[str], list[tuple[dict[str, float], float, float]]]:
    """Two cooldown episodes, the second with a degraded thermal path on A."""
    pids = ["A", "B", "C"]
    gains = {"A": 0.55, "B": 0.9, "C": 0.7}
    sweeps = []
    for tau_map, t0 in (
        ({p: 200.0 for p in pids}, 0.0),
        ({"A": 320.0, "B": 200.0, "C": 200.0}, 500000.0),
    ):
        for i in range(45):
            t = t0 + i * 4.0
            temps = {
                p: 25.0 + gains[p] * 40.0 * math.exp(-(i * 4.0) / tau_map[p])
                for p in pids
            }
            sweeps.append((temps, 25.0, t))
    return pids, sweeps


def _dropout_sweeps() -> tuple[list[str], list[tuple[dict[str, float], float, float]]]:
    """A sensor that stops responding mid-run."""
    pids, sweeps = _panel_sweeps()
    for i in range(len(sweeps) - 10, len(sweeps)):
        temps, amb, t = sweeps[i]
        sweeps[i] = ({k: v for k, v in temps.items() if k != "L2"}, amb, t)
    return pids, sweeps


def _near_ambient_sweeps() -> tuple[
    list[str], list[tuple[dict[str, float], float, float]]
]:
    """Everything parked below the log floor, then lifted above it."""
    pids = ["A", "B", "C"]
    sweeps = []
    for i in range(30):
        sweeps.append(({p: 25.2 for p in pids}, 25.0, i * 4.0))
    for i in range(30, 120):
        sweeps.append(({p: 45.0 + 0.1 * (hash(p) % 3) for p in pids}, 25.0, i * 4.0))
    return pids, sweeps


def _pack(readings) -> tuple[dict[str, float], float, float]:
    return (
        {r.point_id: r.temp_c for r in readings},
        readings[0].ambient_c,
        readings[0].t_s,
    )


SCENARIOS = {
    "three_phase_panel_with_fault": _panel_sweeps,
    "cooldown_tau_shift": _cooldown_sweeps,
    "sensor_dropout": _dropout_sweeps,
    "near_ambient_floor": _near_ambient_sweeps,
}


def main() -> int:
    lib = build_library()
    total = 0
    for name, factory in SCENARIOS.items():
        pids, sweeps = factory()
        divs = compare(pids, sweeps, lib=lib)
        status = "OK  " if not divs else "FAIL"
        print(f"[{status}] {name:<32} {len(sweeps):>4} sweeps x {len(pids)} points")
        for d in divs[:5]:
            print(f"         {d}")
        if len(divs) > 5:
            print(f"         ... and {len(divs) - 5} more")
        total += len(divs)

    print()
    if total:
        print(f"PARITY FAILED: {total} divergences")
        return 1
    print("PARITY PROVEN: C and Python agree on every scenario")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
