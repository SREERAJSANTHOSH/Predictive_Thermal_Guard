# Engineering notes

This file is the bench log. Record what happened, including failed attempts,
instead of rewriting the result as if the first wiring worked.

## Software verification

Date: 2026-07-28

- Python version: 3.12.13
- `pytest` result: 11 passed
- PlatformIO environment: `esp32dev`, Espressif32 6.10.0, Arduino framework
- `pio run` result: success
- Firmware size: 45,176 bytes RAM (13.8%), 773,533 bytes flash (59.0%)
- GUI smoke check: main window created with the Qt off-screen platform
- Notes: software-only validation; no serial, sensor, Wi-Fi, or MQTT hardware
  result is implied by these checks.

## Bench session 1 — host bus and mux

Date:

Setup:

- ESP32 board:
- TCA9548A board:
- USB supply:
- SDA/SCL pins:
- I2C clock:

Measurements:

- 3.3 V rail:
- TCA9548A address found:
- Reset pin voltage:
- Effective SDA/SCL pull-up resistance:

Problems and changes:

- _Not tested yet._

## Bench session 2 — first MLX90614

Date:

- Mux channel:
- Sensor board:
- Sensor address:
- Ambient reference thermometer:
- MLX90614 ambient reading:
- Object target and distance:
- MLX90614 object reading:
- Read failures over 10 minutes:

Problems and changes:

- _Not tested yet._

## Bench session 3 — multiple sensors and MQTT

Date:

- Connected channels:
- Publish interval measured:
- Broker machine / OS:
- Messages observed with `mosquitto_sub`:
- Queue drops printed over Serial:
- Wi-Fi reconnect test:
- MQTT reconnect test:

Problems and changes:

- _Not tested yet._

## Fault trial

Do not use mains equipment for the first trial. Use a low-voltage, controlled
heat source and keep within the sensor and target ratings.

Date:

- Baseline duration:
- Baseline mean by channel:
- Heat source:
- Target distance:
- Threshold settings:
- First flagged temperature:
- Time to flag:
- False alerts:

Observation:

- _Not tested yet._
