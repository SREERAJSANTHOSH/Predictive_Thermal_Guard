# Thermal Symmetry Guard

![CI](https://github.com/SREERAJSANTHOSH/Predictive_Thermal_Guard/actions/workflows/ci.yml/badge.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**A differential thermography engine that finds thermal faults — loose lugs, degraded thermal paths — without ever knowing or needing surface emissivity.**

Thermal Symmetry Guard compares *sibling* measurement points against each other instead of against absolute thresholds. Emissivity, view-factor errors, and ambient/load swings cancel out mathematically, leaving only the real anomaly signal.

> An absolute-threshold detector flags a healthy busbar at 64.8 °C while missing a genuine loose-lug fault at 49.5 °C.
> Thermal Symmetry Guard flags the fault correctly — because it doesn't need to know what temperature anything *should* be.

---

## 📐 Core Insight

For any warm surface viewed by an IR sensor, the apparent temperature rise above ambient is:

```
rise_apparent = g × rise_true        where g = ε × view_factor (unknown)
```

Taking logarithms makes the unknown gain **additive**:

```
log(rise_apparent) = log(g) + log(rise_true)
```

Subtracting the **peer median** and each point's **learned offset** removes emissivity completely — no calibration, no contact probes, no lookup tables. What remains is a pure fault signal.

The engine also recovers the **cooldown time constant τ** from the slope of `log(rise)` vs time during cooling. Because emissivity only shifts the intercept and never the slope, τ is absolute and calibration-free. A change in τ means the thermal path has degraded — often *before* temperatures move.

## ⚡ Demo

Three-phase panel with emissivities **0.55 / 0.95 / 0.72** — none of which are known to the engine:

| Stage | L1 (ε = 0.55) | L2 (ε = 0.95) | L3 (ε = 0.72) |
|---|---|---|---|
| Steady load | ✅ symmetric, z = −0.02 | ✅ symmetric, z = +0.00 | ✅ symmetric, z = +0.30 |
| 35 K shared ramp | ✅ common\_mode\_rise | ✅ common\_mode\_rise | ✅ common\_mode\_rise |
| L1 loose lug +7 K | 🔴 asymmetric\_hot, z = +5.9 | ✅ common\_mode\_rise | ✅ common\_mode\_rise |

L1 is flagged at **49.5 °C** while healthy L2 sits at **64.8 °C**. An absolute-threshold detector gets this exactly backwards.

## 🏗️ Project Structure

```text
src/thermal_symmetry_guard/       Python reference engine
  types.py                        Verdict, Reading, ChannelReport, GroupReport
  robust.py                       RobustBaseline (median/MAD), Cusum, TrendFilter
  symmetry.py                     SymmetryGroup, Channel, TauEstimator
  scenarios.py                    Synthetic test rigs
  demo.py                         Runnable narrative demo

firmware/                         ESP32 PlatformIO project
  include/symmetry.h              C API and data structures
  src/symmetry.c                  Line-by-line port of the Python core
  src/main.cpp                    Application layer (I2C, MLX90614, serial output)

tests/                            69 tests (pytest)
  test_robust.py                  Statistics primitives
  test_symmetry.py                Engine scenarios
  test_tau.py                     Cooldown signature
  test_parity.py                  C ↔ Python numerical agreement

tools/parity.py                   Builds shared lib and drives both implementations
hardware/                         Wiring diagram, BOM
docs/THEORY.md                    Full mathematical derivation
.github/workflows/ci.yml          CI on Python 3.10–3.12
```

### Hardware

- **MCU:** ESP32
- **Sensors:** MLX90614 IR thermopile (non-contact)
- **Multiplexer:** TCA9548A I2C mux
- **Firmware footprint:** heap-free, ~8 KB for 8 measurement points

## 🚀 Quick Start

### Python Reference Engine

```bash
pip install -e '.[dev]'
python -m thermal_symmetry_guard.demo
```

### Firmware (ESP32)

```bash
cd firmware
pio run            # build
pio run -t upload  # flash
```

### Tests

```bash
pytest
```

All 69 tests cover statistics primitives, engine scenarios, cooldown-signature extraction, and C ↔ Python numerical parity.

## 🏷️ Verdicts

Every measurement point receives one of these verdicts on each sweep:

| Verdict | Meaning |
|---|---|
| `warming_up` | Commissioning phase or reading below the log-domain floor |
| `symmetric` | In step with peers — no anomaly |
| `common_mode_rise` | Whole group is heating — load or ambient change, not a fault |
| `asymmetric_hot` | Hotter than siblings — potential fault |
| `asymmetric_cold` | Colder than siblings — potential fault |
| `tau_shift` | Thermal time constant has changed — degraded thermal path |
| `sensor_suspect` | No valid reading for 3 consecutive sweeps |

## 🎯 What Makes It Different

Compared to conventional IR thermography and fixed-threshold monitors:

| | Conventional | Thermal Symmetry Guard |
|---|---|---|
| **Emissivity calibration** | Required (contact probe / lookup table) | Not needed — ever |
| **Ambient / load swings** | Frequent false alarms | Common-mode rejection cancels them |
| **Degraded thermal path** | Invisible until temperature rises | Detected early via τ shift |
| **Commissioning** | Manual setpoint configuration | Self-commissioning — just run the equipment |
| **Contact probes** | Often required for reference | Fully non-contact |

## 📖 Theory

The full mathematical derivation — log-domain emissivity cancellation, robust statistics, τ recovery, and CUSUM change detection — is in [`docs/THEORY.md`](docs/THEORY.md).

## 🧪 Dual Implementation

The project ships two numerically identical implementations:

- **Python** (`src/thermal_symmetry_guard/`) — reference engine for prototyping, simulation, and testing.
- **C** (`firmware/src/symmetry.c`) — line-by-line port targeting ESP32. Heap-free, deterministic, suitable for safety-adjacent embedded use.

The `test_parity.py` suite and `tools/parity.py` driver build the C code as a shared library and verify bit-level agreement between the two implementations across all engine paths.

## 📄 License

[Apache 2.0](LICENSE) — Sreeraj Santhosh
