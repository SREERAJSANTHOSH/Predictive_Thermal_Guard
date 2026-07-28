# Telemetry protocol

## MQTT

Topic:

```text
thermal-guard/{device_id}/telemetry
```

Recommended settings: QoS 1, 60-second keep-alive, retained flag disabled.

## Device envelope

```json
{
  "device_id": "EM-PANEL-1",
  "firmware_version": "2.0.0",
  "uptime_s": 48291,
  "rssi_dbm": -54,
  "readings": [
    {
      "device_id": "EM-PANEL-1",
      "sensor_id": "L1",
      "temperature_c": 45.6,
      "ambient_c": 29.2
    }
  ]
}
```

POST the same envelope to `/api/v1/telemetry`.

## Generic reading

Any gateway or sensor can POST `/api/v1/readings`:

```json
{
  "device_id": "boiler-room-gateway",
  "sensor_id": "bearing-4",
  "temperature_c": 61.3,
  "ambient_c": 27.8,
  "timestamp": "2026-07-28T10:24:36Z"
}
```

## Thermal frame

POST `/api/v1/frames`. `pixels_c` is a row-major array and its length must equal
`width × height`.

```json
{
  "device_id": "camera-a",
  "camera_id": "mlx90640",
  "width": 4,
  "height": 3,
  "pixels_c": [31, 32, 34, 35, 31, 33, 72, 36, 30, 31, 34, 33]
}
```

The service stores the frame, locates its hottest pixel, evaluates the maximum
temperature using the same detector, and sends the updated snapshot to
WebSocket clients.
