#pragma once

// Safe development defaults. Override these values with PlatformIO build flags
// or copy them into an ignored config.local.h for a real deployment.
#define PTG_WIFI_SSID "replace-me"
#define PTG_WIFI_PASSWORD "replace-me"
#define PTG_MQTT_HOST "192.168.1.10"
#define PTG_MQTT_PORT 1883
#define PTG_HTTP_ENDPOINT "http://192.168.1.10:8000/api/v1/telemetry"
#define PTG_DEVICE_ID "EM-PANEL-1"
#define PTG_FIRMWARE_VERSION "0.2.0"
#define PTG_SAMPLE_INTERVAL_MS 1000
#define PTG_PUBLISH_MQTT 1
#define PTG_PUBLISH_HTTP 1
