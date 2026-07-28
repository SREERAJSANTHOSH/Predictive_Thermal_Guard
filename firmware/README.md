# ESP32 firmware

The firmware reads up to eight same-address MLX90614 sensors through a
TCA9548A I²C multiplexer and publishes a validated telemetry envelope over MQTT
and/or HTTP.

## Wiring

| ESP32 | TCA9548A / sensors |
|---|---|
| 3V3 | VIN |
| GND | GND |
| GPIO 21 | SDA |
| GPIO 22 | SCL |

Attach each MLX90614 to a separate TCA9548A channel. The default build uses
channels 0–2 as phases L1–L3.

## Build and upload

```bash
pio run -d firmware
pio run -d firmware -t upload
pio device monitor -b 115200
```

Edit `include/config.h` for development or override every `PTG_*` value using
PlatformIO build flags in a private environment.
