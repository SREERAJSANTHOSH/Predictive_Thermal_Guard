# Architecture

Predictive Thermal Guard separates device acquisition, ingestion/analytics, and
visualization so each layer can be tested and deployed independently.

## Device layer

The ESP32 samples three MLX90614 thermopiles through channels 0–2 of a
TCA9548A. Up to eight sensors can share the same I²C address because only one
multiplexer channel is active at a time. Each batch includes object
temperature, sensor ambient temperature, RSSI, uptime, and firmware version.

MQTT is the primary transport for low-overhead continuous telemetry. HTTP uses
the same JSON envelope and acts as a direct or fallback transport.

## Service layer

FastAPI validates all payloads before persistence. SQLite is the default
zero-configuration store; the repository boundary makes a PostgreSQL adapter a
straightforward production extension.

The analyzer keeps an exponentially weighted baseline per `(device, sensor)`.
It combines:

- absolute warning and critical temperature limits;
- adaptive z-score detection after baseline warm-up;
- thermal-frame minimum, maximum, and hotspot coordinates.

Every accepted update is available through REST and broadcast to dashboard
clients over WebSockets.

## Dashboard layer

The dashboard renders thermal frames as data—not as a static image—so each cell
remains inspectable. It attempts the configured API and WebSocket endpoints,
then falls back to deterministic demonstration data for offline presentations.

## Security boundary

The included Mosquitto configuration is intentionally local-development only.
A production deployment should add TLS, per-device credentials, authorization
by topic, an API gateway, and rate limits. Device secrets should never be
committed to `firmware/include/config.h`; use private build flags or a local
override.
