# Architecture

Predictive Thermal Guard separates device acquisition, ingestion/analytics, and
visualization so each layer can be tested and deployed independently.

## Device layer

The ESP32 samples three MLX90614 thermopiles through channels 0–2 of a
TCA9548A. Up to eight sensors can share the same I²C address because only one
multiplexer channel is active at a time. Each batch includes object
temperature, sensor ambient temperature, RSSI, uptime, and firmware version.

MQTT and HTTP use the same JSON envelope. The current firmware attempts every
enabled transport on each cycle. Conditional fallback, retry buffering, and
deduplication are planned but are not implemented in version 0.2.

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

An alert records its cause (`absolute_warning`, `absolute_critical`, or
`adaptive`) so a statistical deviation is not displayed as if it crossed the
fixed warning temperature.

## Dashboard layer

The dashboard renders thermal frames as data—not as a static image—so each cell
remains inspectable. It attempts the configured API and WebSocket endpoints,
then switches to clearly labelled deterministic demonstration data. The
demonstration temperature profile is an interface fixture, not experimental
evidence.

## Security boundary

The included Mosquitto configuration is intentionally local-development only.
A production deployment should add TLS, per-device credentials, authorization
by topic, an API gateway, and rate limits. Device secrets should never be
committed to `firmware/include/config.h`; use private build flags or a local
override.
