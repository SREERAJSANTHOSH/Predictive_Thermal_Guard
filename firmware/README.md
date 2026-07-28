# Firmware

`src/symmetry.c` is a line-by-line port of the Python reference in
`src/thermal_symmetry_guard/`. Keep them in sync: if you change a threshold in
one, change it in the other, and add a test in `tests/`.

Deliberate properties of the embedded core:

- **No heap.** Every buffer is sized at compile time (`TSG_MAX_POINTS`,
  `TSG_WINDOW`, `TSG_TAU_SEGMENT`). Total footprint is roughly
  `TSG_MAX_POINTS * (2 * TSG_WINDOW + TSG_TAU_SEGMENT * 2) * 4` bytes ≈ 8 KB
  for 8 points.
- **No fourth powers.** The only transcendental call is `logf()` on a
  temperature rise. Nothing in the signal path can overflow: a Stefan-Boltzmann
  style `T⁴` in scaled integers reaches ~10²⁰ and silently wraps a 64-bit
  accumulator, which is exactly the class of bug this design avoids by never
  needing an absolute radiometric model.
- **No calibration state to persist.** The learned offsets live in RAM and are
  re-acquired during commissioning after a reboot. Persist them to NVS only if
  you want to skip the warm-up; nothing else depends on them.

## Build

```bash
cd firmware
pio run              # build
pio run -t upload    # flash
pio device monitor   # 115200 baud
```

## Wiring

See [../hardware/WIRING.md](../hardware/WIRING.md).
