# Thermal Fault Guard

Electrical panels, cable joints, and connectors can develop local hot spots
before there is visible damage. Thermal Fault Guard is an ECE prototype that
uses non-contact IR sensors on an ESP32 to watch several points continuously.
A TCA9548A multiplexer lets the controller read multiple MLX90614 sensors that
all use the same I2C address. Readings are sent over MQTT, checked against a
rolling per-channel baseline, logged to CSV, and displayed in a PyQt desktop
application.

I kept this project close to the embedded systems, FreeRTOS, networking,
Python/PyQt, and PCB work in my ECE background . The
firmware and hardware interfaces are the main part of the project; the PC
software is deliberately a small lab tool rather than a web platform.

## Current status

- ESP32 firmware: implemented for four mux channels
- FreeRTOS sensor and MQTT tasks: implemented
- MQTT-to-CSV monitor and rolling-average check: implemented and unit tested
- PyQt5 table and matplotlib history plot: implemented
- Breadboard wiring and KiCad module-level schematic: documented
- Physical bench test and prototype photographs: **to be completed on the
  actual hardware**

The repository does not claim fabricated hardware, calibration data, or test
results that have not been measured.

## System outline

```mermaid
flowchart LR
    S["4 × MLX90614"] --> M["TCA9548A"]
    M --> E["ESP32<br/>2 FreeRTOS tasks"]
    E --> Q["Mosquitto MQTT"]
    Q --> P["Python monitor<br/>CSV + baseline"]
    P --> G["PyQt dashboard"]
```

The sensor task polls channels 0 to 3 once per second. It passes a compact
reading structure through a FreeRTOS queue. The MQTT task owns the network
client and publishes each queued sample to:

```text
thermal-fault-guard/<device-id>/temperature
```

Example payload:

```json
{
  "device_id": "panel-a",
  "channel": 0,
  "temp_c": 42.3,
  "ambient_c": 28.1,
  "uptime_ms": 15120,
  "sequence": 17,
  "valid": true
}
```

## Hardware

The expected prototype is an ESP32 DevKit, one TCA9548A breakout, and two to
four MLX90614 breakout boards. Start with one sensor and add the others only
after the host bus and mux address have been checked.

- [Wiring table](hardware/WIRING.md)
- [Bill of materials](hardware/BOM.md)
- [KiCad source and design notes](hardware/README.md)
- [Prototype photo checklist](hardware/photos/README.md)

> Prototype photo placeholder: add
> `hardware/photos/breadboard-overview.jpg` after the real assembly has been
> photographed.

## Run it

### 1. Start Mosquitto

Install Mosquitto using the package for your operating system, then run a
local broker:

```bash
mosquitto -v
```

In another terminal, watch the raw device messages:

```bash
mosquitto_sub -v -t 'thermal-fault-guard/+/temperature'
```

### 2. Configure and flash the ESP32

Edit the lab-network values in `firmware/include/config.h`. Do not commit a
real Wi-Fi password. With PlatformIO installed:

```bash
cd firmware
pio run
pio run --target upload
pio device monitor
```

Expected serial output identifies every available mux channel and prints the
object and ambient temperature once per poll.

### 3. Start the CSV monitor

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
thermal-monitor --broker localhost --csv temperature_log.csv
```

The default detector needs eight earlier readings for a channel. It flags an
absolute deviation of 8 °C or more, or any reading at or above 85 °C. These
are lab defaults, not safety-certified limits:

```bash
thermal-monitor \
  --broker localhost \
  --window 20 \
  --minimum-samples 8 \
  --deviation 8 \
  --critical 85
```

### 4. Open the desktop dashboard

Keep the monitor running and open another activated terminal:

```bash
thermal-dashboard --csv temperature_log.csv
```

The table shows the latest value for each channel. A fault row turns red, and
fault samples are marked with red crosses on the history plot.

## Software checks

```bash
python -m pip install -e '.[test]'
pytest
```

The test suite covers payload validation, independent channel baselines, fault
detection, CSV writing, and dashboard CSV parsing. Firmware compilation is
checked separately with `pio run`.

## Repository layout

| Path | Purpose |
|---|---|
| `firmware/` | ESP32 Arduino/FreeRTOS firmware |
| `backend/monitor.py` | MQTT subscriber, detector, and CSV logger |
| `desktop/` | PyQt5 and matplotlib desktop dashboard |
| `hardware/` | BOM, wiring, KiCad source, and photo checklist |
| `tests/` | Python unit tests |
| `NOTES.md` | Bench log for real measurements and faults |

## Known limitations

- The hardware path has not been bench-verified in this repository yet.
- MLX90614 readings depend on target emissivity, distance, field of view, and
  sensor placement; this prototype does not compensate for all of them.
- The rolling average is intentionally simple. A slow-moving fault can become
  part of the baseline.
- The MQTT connection is plain text and intended only for a trusted lab LAN.
- CSV is easy to inspect but the GUI rereads it on every refresh. SQLite is a
  sensible next step for longer tests.
- This is a monitoring prototype, not a certified protection or shutdown
  device.

My next hardware step is to assemble two sensors on the mux, record the I2C
and timing problems in `NOTES.md`, then update the KiCad drawing from the
actual breadboard before considering a PCB layout.

## License

MIT — see [LICENSE](LICENSE).
