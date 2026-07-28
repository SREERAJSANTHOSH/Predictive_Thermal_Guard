#include <Adafruit_MLX90614.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <Wire.h>

#include "config.h"
#include "telemetry.h"

namespace {

constexpr uint8_t kMuxAddress = 0x70;
constexpr uint8_t kSensorCount = 3;
constexpr uint8_t kMuxChannels[kSensorCount] = {0, 1, 2};
constexpr const char *kSensorIds[kSensorCount] = {"L1", "L2", "L3"};

WiFiClient network_client;
PubSubClient mqtt_client(network_client);
Adafruit_MLX90614 sensors[kSensorCount];
uint32_t last_sample_ms = 0;

bool select_mux_channel(uint8_t channel) {
  if (channel > 7) {
    return false;
  }
  Wire.beginTransmission(kMuxAddress);
  Wire.write(static_cast<uint8_t>(1U << channel));
  return Wire.endTransmission() == 0;
}

void connect_wifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(PTG_WIFI_SSID, PTG_WIFI_PASSWORD);
  Serial.print("Wi-Fi");
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) {
    delay(250);
    Serial.print('.');
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " connected" : " timeout");
}

void connect_mqtt() {
#if PTG_PUBLISH_MQTT
  if (mqtt_client.connected() || WiFi.status() != WL_CONNECTED) {
    return;
  }
  const String client_id = String("ptg-") + PTG_DEVICE_ID + "-" +
                           String(static_cast<uint32_t>(ESP.getEfuseMac()), HEX);
  mqtt_client.connect(client_id.c_str());
#endif
}

void initialize_sensors() {
  for (uint8_t index = 0; index < kSensorCount; ++index) {
    if (!select_mux_channel(kMuxChannels[index])) {
      Serial.printf("TCA9548A channel %u unavailable\n", kMuxChannels[index]);
      continue;
    }
    if (!sensors[index].begin(0x5A, &Wire)) {
      Serial.printf("MLX90614 %s unavailable\n", kSensorIds[index]);
    }
  }
}

TelemetryBatch sample_sensors() {
  TelemetryBatch batch{};
  batch.count = kSensorCount;
  batch.uptime_s = millis() / 1000;
  batch.rssi_dbm = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127;

  for (uint8_t index = 0; index < kSensorCount; ++index) {
    ThermalReading &reading = batch.readings[index];
    strlcpy(reading.sensor_id, kSensorIds[index], sizeof(reading.sensor_id));
    if (!select_mux_channel(kMuxChannels[index])) {
      reading.valid = false;
      continue;
    }
    reading.object_c = sensors[index].readObjectTempC();
    reading.ambient_c = sensors[index].readAmbientTempC();
    reading.valid = isfinite(reading.object_c) && isfinite(reading.ambient_c);
  }
  return batch;
}

size_t serialize_batch(const TelemetryBatch &batch, char *payload,
                       size_t capacity) {
  JsonDocument document;
  document["device_id"] = PTG_DEVICE_ID;
  document["firmware_version"] = PTG_FIRMWARE_VERSION;
  document["uptime_s"] = batch.uptime_s;
  document["rssi_dbm"] = batch.rssi_dbm;
  JsonArray readings = document["readings"].to<JsonArray>();
  for (uint8_t index = 0; index < batch.count; ++index) {
    const ThermalReading &reading = batch.readings[index];
    if (!reading.valid) {
      continue;
    }
    JsonObject item = readings.add<JsonObject>();
    item["device_id"] = PTG_DEVICE_ID;
    item["sensor_id"] = reading.sensor_id;
    item["temperature_c"] = serialized(String(reading.object_c, 2));
    item["ambient_c"] = serialized(String(reading.ambient_c, 2));
  }
  return serializeJson(document, payload, capacity);
}

bool publish_mqtt(const char *payload, size_t length) {
#if PTG_PUBLISH_MQTT
  connect_mqtt();
  if (!mqtt_client.connected()) {
    return false;
  }
  const String topic = String("thermal-guard/") + PTG_DEVICE_ID + "/telemetry";
  return mqtt_client.publish(topic.c_str(),
                             reinterpret_cast<const uint8_t *>(payload), length,
                             false);
#else
  (void)payload;
  (void)length;
  return false;
#endif
}

bool publish_http(const char *payload) {
#if PTG_PUBLISH_HTTP
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  HTTPClient http;
  http.begin(PTG_HTTP_ENDPOINT);
  http.addHeader("Content-Type", "application/json");
  const int status = http.POST(String(payload));
  http.end();
  return status >= 200 && status < 300;
#else
  (void)payload;
  return false;
#endif
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);
  connect_wifi();
  mqtt_client.setServer(PTG_MQTT_HOST, PTG_MQTT_PORT);
  mqtt_client.setBufferSize(2048);
  initialize_sensors();
  Serial.println("Predictive Thermal Guard firmware ready");
}

void loop() {
  connect_wifi();
  connect_mqtt();
  mqtt_client.loop();

  const uint32_t now = millis();
  if (now - last_sample_ms < PTG_SAMPLE_INTERVAL_MS) {
    delay(10);
    return;
  }
  last_sample_ms = now;

  const TelemetryBatch batch = sample_sensors();
  char payload[2048];
  const size_t length = serialize_batch(batch, payload, sizeof(payload));
  if (length == 0 || length >= sizeof(payload)) {
    Serial.println("Telemetry serialization failed");
    return;
  }

  const bool mqtt_ok = publish_mqtt(payload, length);
  const bool http_ok = publish_http(payload);
  Serial.printf("Telemetry bytes=%u mqtt=%s http=%s\n",
                static_cast<unsigned>(length), mqtt_ok ? "ok" : "skip/fail",
                http_ok ? "ok" : "skip/fail");
}
