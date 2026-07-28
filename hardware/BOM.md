# Bill of Materials — 3-Point Thermal Symmetry Guard

This BOM covers a single sensor node capable of monitoring **3 thermal points** using non-contact IR thermometry.

---

## Parts List

| # | Part | Qty | Approx Cost | Notes |
|---|------|-----|-------------|-------|
| 1 | ESP32-WROOM-32 dev board | 1 | $4–8 | Any ESP32 dev board (NodeMCU-32S, DevKitC, etc.). ESP32-S3 also supported. |
| 2 | MLX90614ESF-BAA | 3 | $8–12 each | TO-39 can package, 90° FOV. Medical-grade (BAA suffix) recommended for accuracy. |
| 3 | TCA9548A breakout board | 1 | $2–4 | Adafruit #2717 or generic equivalent. 8-channel I²C multiplexer. |
| 4 | 4.7 kΩ resistors | 2 | $0.10 | ¼W, through-hole or SMD. I²C pull-ups on master bus. |
| 5 | 100 nF ceramic capacitors | 3 | $0.30 | C0G/X7R, through-hole or SMD. One bypass cap per MLX90614 sensor. |
| 6 | Hookup wire | — | $2 | 22 AWG solid-core recommended for breadboard use. |
| 7 | Breadboard or prototype PCB | 1 | $2–5 | Half-size breadboard sufficient for 3 sensors. |

---

## Cost Summary

| | Low Estimate | High Estimate |
|---|---|---|
| ESP32 dev board | $4 | $8 |
| 3× MLX90614 | $24 | $36 |
| TCA9548A breakout | $2 | $4 |
| Passives (resistors + caps) | $0.40 | $0.40 |
| Wire + breadboard | $4 | $7 |
| **Total** | **~$35** | **~$55** |

> **Typical build cost: $45–65** depending on supplier and shipping.

---

## Scaling to 8 Points

The TCA9548A multiplexer has **8 channels**. The same hardware design supports up to 8 MLX90614 sensors without any additional multiplexers or bus changes.

| Configuration | Additional Parts | Incremental Cost |
|---------------|-----------------|-----------------|
| 4 sensors | +1 MLX90614, +1 bypass cap | ~$8–12 |
| 6 sensors | +3 MLX90614, +3 bypass caps | ~$24–36 |
| 8 sensors (max per mux) | +5 MLX90614, +5 bypass caps | ~$40–60 |

At 8 sensors, total system current remains under 35 mA — well within the ESP32's on-board 3.3V regulator capacity.

> [!TIP]
> For installations requiring more than 8 monitoring points, add a second TCA9548A at a different address (set A0 high → address 0x71) to support up to 16 sensors on a single ESP32.

---

## Sourcing Notes

- **MLX90614ESF-BAA**: Available from Mouser, DigiKey, and AliExpress. The BAA variant has the widest FOV (90°). The DCI variant (5° FOV) is available for long-range spot measurements but is not recommended for this application.
- **TCA9548A breakout**: Adafruit, SparkFun, and generic boards from AliExpress are all compatible. Ensure the board exposes all 8 channel pairs (SDx/SCx).
- **ESP32 boards**: Any board with exposed GPIO 21/22 (or GPIO 8/9 for S3) and a 3.3V output pin is suitable.

---

## Tools Required

| Tool | Purpose |
|------|---------|
| Soldering iron (optional) | If using a proto PCB instead of breadboard |
| Wire strippers | For hookup wire |
| Multimeter | Verify 3.3V rail, check I²C pull-up resistance |
| USB cable (micro-USB or USB-C) | ESP32 programming and power |
