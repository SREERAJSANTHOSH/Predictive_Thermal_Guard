# ESP32 firmware

The firmware uses Arduino libraries on the ESP32, but the application work is
split into two FreeRTOS tasks.

| Task | Core | Priority | Responsibility |
|---|---:|---:|---|
| `sensor-poll` | 1 | 2 | Select mux channel, read MLX90614, queue sample |
| `mqtt-publish` | 0 | 1 | Maintain Wi-Fi/MQTT and publish queued samples |

`loop()` is deliberately idle. The queue is the boundary between I2C timing
and network timing, so a slow broker connection does not own the sensor bus.
If the 16-element queue fills, the oldest pending sample is discarded and a
message is printed over Serial.

## Mux selection

The TCA9548A is at address `0x70`. A channel is connected by writing a byte
with only that channel's bit set:

```cpp
Wire.beginTransmission(0x70);
Wire.write(1U << channel);
Wire.endTransmission();
```

For channel 2, the byte is `00000100`. This explicit operation matters because
every downstream MLX90614 normally responds at `0x5A`.

## Configuration

Edit `include/config.h` before flashing:

- Wi-Fi SSID and password
- Mosquitto broker IPv4 address
- device ID
- publish topic

The committed values are placeholders. Never put a real network password in a
public commit.

## Build

```bash
pio run
pio run --target upload
pio device monitor
```

The initial hardware test should use only channels 0 and 1. The code probes
all four configured channels and marks a channel unavailable if sensor
initialisation fails.
