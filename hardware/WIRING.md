# Wiring Guide — ESP32 + TCA9548A + MLX90614

This document describes how to wire a 3-point Thermal Symmetry Guard sensor node using an ESP32 microcontroller, a TCA9548A I²C multiplexer, and three MLX90614 non-contact IR temperature sensors.

---

## Components

| Component | Role |
|-----------|------|
| ESP32-WROOM-32 (or ESP32-S3) dev board | Microcontroller, I²C master |
| TCA9548A I²C multiplexer breakout | Routes I²C bus to individual sensors |
| MLX90614ESF-BAA × 3 | Non-contact IR temperature sensors |
| 4.7 kΩ resistors × 2 | I²C pull-ups on the master bus |
| 100 nF ceramic capacitors × 3 | Bypass decoupling, one per sensor |

---

## Pin Assignments

### ESP32-WROOM-32

| Signal | GPIO | Notes |
|--------|------|-------|
| SDA | GPIO 21 | Default I²C data |
| SCL | GPIO 22 | Default I²C clock |
| 3.3V | 3V3 pin | Powers mux and sensors |
| GND | GND | Common ground |

### ESP32-S3

| Signal | GPIO | Notes |
|--------|------|-------|
| SDA | GPIO 8 | Default I²C data |
| SCL | GPIO 9 | Default I²C clock |
| 3.3V | 3V3 pin | Powers mux and sensors |
| GND | GND | Common ground |

### TCA9548A Multiplexer

| Pin | Connection | Notes |
|-----|------------|-------|
| VIN | 3.3V | Supply voltage |
| GND | GND | Common ground |
| SDA | ESP32 SDA | Master I²C data |
| SCL | ESP32 SCL | Master I²C clock |
| A0, A1, A2 | GND | Sets mux address to **0x70** |
| SD0/SC0 | MLX90614 #0 SDA/SCL | Mux channel 0 |
| SD1/SC1 | MLX90614 #1 SDA/SCL | Mux channel 1 |
| SD2/SC2 | MLX90614 #2 SDA/SCL | Mux channel 2 |

### MLX90614 (each sensor, identical wiring)

| Pin | Connection |
|-----|------------|
| VCC | 3.3V (through 100 nF bypass cap to GND) |
| GND | GND |
| SDA | Mux channel SDx |
| SCL | Mux channel SCx |

All three MLX90614 sensors share the same I²C address (**0x5A**). The TCA9548A mux isolates them onto separate channels, allowing the ESP32 to address each sensor individually by selecting the appropriate mux channel before each read.

---

## I²C Pull-Ups

Two **4.7 kΩ** resistors are required on the **master-side** I²C bus (between the ESP32 and the TCA9548A):

- One from **SDA** to **3.3V**
- One from **SCL** to **3.3V**

> [!NOTE]
> Many ESP32 and TCA9548A breakout boards include on-board pull-ups. If both boards have pull-ups enabled, the effective resistance is halved (~2.35 kΩ), which is acceptable for 100 kHz I²C at 3.3V. If you experience communication errors at 400 kHz, remove the external resistors and rely on on-board pull-ups alone.

Do **not** add pull-ups on the downstream mux channels. The TCA9548A provides bidirectional FET switches, and the master-side pull-ups serve all channels.

---

## Bypass Capacitors

Place a **100 nF (0.1 µF)** ceramic capacitor between VCC and GND on each MLX90614, as close to the sensor pins as physically possible. This decouples high-frequency noise from the sensor's internal ADC and prevents I²C glitches caused by supply transients.

---

## ASCII Wiring Diagram

```
                          +3.3V
                            │
                       ┌────┴────┐
                       │  4.7kΩ  │  4.7kΩ
                       │    │         │
                       │    │         │
  ┌────────────────┐   │    │         │      ┌──────────────────┐
  │   ESP32        │   │    │         │      │   TCA9548A       │
  │                │   │    │         │      │   (0x70)         │
  │  GPIO21 (SDA) ─┼───┼────┴─────────┼──────┤ SDA              │
  │  GPIO22 (SCL) ─┼───┼──────────────┴──────┤ SCL              │
  │                │   │                     │                  │
  │  3V3 ──────────┼───┴─────────────────────┤ VIN              │
  │  GND ──────────┼─────────────────────────┤ GND              │
  │                │                         │  A0,A1,A2 → GND  │
  └────────────────┘                         │                  │
                                             │  CH0 SD0/SC0 ────┼──── MLX90614 #0
                                             │  CH1 SD1/SC1 ────┼──── MLX90614 #1
                                             │  CH2 SD2/SC2 ────┼──── MLX90614 #2
                                             └──────────────────┘

  Each MLX90614 (identical wiring):

       +3.3V ────┬──── VCC (MLX90614)
                  │
              ┌───┴───┐
              │100 nF │
              └───┬───┘
                  │
       GND ───────┴──── GND (MLX90614)

       SDx (from mux) ──── SDA (MLX90614)
       SCx (from mux) ──── SCL (MLX90614)

       I²C address: 0x5A (factory default, same for all — mux isolates them)
```

---

## Power Budget

| Component | Typical Draw |
|-----------|-------------|
| MLX90614 × 3 | ~1.5 mA each = **4.5 mA** |
| TCA9548A | ~0.1 mA |
| ESP32 (active, Wi-Fi off) | ~20 mA |
| **Total** | **~25 mA** |

The ESP32's on-board 3.3V regulator (typically rated 500 mA+) has ample headroom. No external regulator is needed for 3 sensors.

> [!TIP]
> The TCA9548A supports 8 channels. You can scale to 8 MLX90614 sensors without any additional multiplexers. At 8 sensors, total current is ~32 mA — still well within the ESP32 regulator's capacity.

---

## Sensor Mounting

### Field of View

The MLX90614ESF-BAA has a **90° field of view** (FOV). Mount each sensor **5–15 cm** from the target surface to achieve a measurement spot of roughly the same diameter as the distance.

| Distance | Approximate Spot Diameter |
|----------|--------------------------|
| 5 cm | ~5 cm |
| 10 cm | ~10 cm |
| 15 cm | ~15 cm |

### Mounting Guidelines

- **Clear line of sight.** Ensure no obstructions (wires, brackets, other sensors) cross the sensor's FOV cone.
- **Perpendicular aim.** Point the sensor normal to the target surface. Off-axis angles reduce effective emissivity and introduce cosine error.
- **Vibration isolation.** On motor housings, use rubber grommets or silicone standoffs to decouple sensor vibration from the motor.
- **Thermal isolation from sensor body.** Avoid mounting the sensor on a hot surface. The MLX90614 compensates for its own die temperature, but extreme ambient gradients degrade accuracy.
- **Cable routing.** Keep I²C wires short (< 30 cm per channel). For longer runs, reduce I²C clock to 100 kHz and use shielded cable.

---

## I²C Software Configuration

```
Bus speed:       100 kHz (standard mode) — recommended for reliability
                 400 kHz (fast mode) — acceptable if wires are short
Mux address:     0x70 (A0=A1=A2=GND)
Sensor address:  0x5A (all sensors, accessed via mux channel selection)
```

### Channel Selection Sequence

To read sensor $n$ (where $n \in \{0, 1, 2\}$):

1. Write `(1 << n)` to the TCA9548A at address `0x70`.
2. Read from the MLX90614 at address `0x5A` on the now-active channel.
3. Repeat for each sensor.

> [!WARNING]
> Always select a mux channel before reading. If the previous channel is still active, you may read from the wrong sensor. Some implementations write `0x00` to the mux after the final read to deselect all channels, preventing bus contention during idle periods.
