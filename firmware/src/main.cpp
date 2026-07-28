#include <Adafruit_MLX90614.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <WiFi.h>

#include "config.h"
#include "thermal_reading.h"

namespace {

constexpr uint8_t kMuxAddress = 0x70;
constexpr uint8_t kSdaPin = 21;
constexpr uint8_t kSclPin = 22;
constexpr uint8_t kSensorChannels[] = {0, 1, 2, 3};
constexpr TickType_t kPollInterval = pdMS_TO_TICKS(1000);
constexpr TickType_t kReconnectInterval = pdMS_TO_TICKS(5000);

Adafruit_MLX90614 sensors[4];
bool sensorAvailable[4] = {false, false, false, false};
uint32_t sequenceNumber = 0;
QueueHandle_t readingQueue = nullptr;
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

bool selectMuxChannel(uint8_t channel) {
  if (channel > 7) {
    return false;
  }

  // The TCA9548A control register uses one bit per downstream channel.
  // Writing 00000100, for example, connects channel 2 to the ESP32 I2C bus.
  Wire.beginTransmission(kMuxAddress);
  Wire.write(1U << channel);
  return Wire.endTransmission() == 0;
}

void disableMuxChannels() {
  Wire.beginTransmission(kMuxAddress);
  Wire.write(0x00);
  Wire.endTransmission();
}

bool initialiseSensors() {
  bool allDetected = true;

  for (size_t index = 0; index < 4; ++index) {
    const uint8_t channel = kSensorChannels[index];
    sensorAvailable[index] =
        selectMuxChannel(channel) && sensors[index].begin();
    if (!sensorAvailable[index]) {
      Serial.printf("MLX90614 not detected on mux channel %u\n", channel);
      allDetected = false;
      continue;
    }
    Serial.printf("MLX90614 ready on mux channel %u\n", channel);
  }

  disableMuxChannels();
  return allDetected;
}

ThermalReading readSensor(size_t index) {
  ThermalReading reading{};
  reading.channel = kSensorChannels[index];
  reading.uptimeMs = millis();
  reading.sequence = sequenceNumber++;

  if (!sensorAvailable[index] || !selectMuxChannel(reading.channel)) {
    return reading;
  }

  reading.objectTempC = sensors[index].readObjectTempC();
  reading.ambientTempC = sensors[index].readAmbientTempC();
  reading.valid = isfinite(reading.objectTempC) &&
                  isfinite(reading.ambientTempC) &&
                  reading.objectTempC > -70.0F &&
                  reading.objectTempC < 380.0F;
  return reading;
}

void sensorTask(void *parameter) {
  (void)parameter;
  TickType_t lastWakeTime = xTaskGetTickCount();

  while (true) {
    for (size_t index = 0; index < 4; ++index) {
      const ThermalReading reading = readSensor(index);
      if (reading.valid) {
        Serial.printf(
            "channel=%u object=%.2f C ambient=%.2f C sequence=%lu\n",
            reading.channel,
            reading.objectTempC,
            reading.ambientTempC,
            static_cast<unsigned long>(reading.sequence));
      } else {
        Serial.printf("channel=%u read failed\n", reading.channel);
      }

      if (xQueueSend(readingQueue, &reading, 0) != pdTRUE) {
        Serial.println("reading queue full; dropping oldest pending sample");
        ThermalReading discarded{};
        xQueueReceive(readingQueue, &discarded, 0);
        xQueueSend(readingQueue, &reading, 0);
      }
    }

    disableMuxChannels();
    vTaskDelayUntil(&lastWakeTime, kPollInterval);
  }
}

void beginWifiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.printf("connecting to Wi-Fi SSID %s\n", config::kWifiSsid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(config::kWifiSsid, config::kWifiPassword);
}

bool connectMqtt() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  const String clientId =
      String("thermal-fault-guard-") + config::kDeviceId + "-" +
      String(static_cast<uint32_t>(ESP.getEfuseMac()), HEX);
  if (mqttClient.connect(clientId.c_str())) {
    Serial.printf("MQTT connected to %s:%u\n",
                  config::kMqttHost,
                  config::kMqttPort);
    return true;
  }

  Serial.printf("MQTT connection failed, state=%d\n", mqttClient.state());
  return false;
}

bool publishReading(const ThermalReading &reading) {
  JsonDocument document;
  document["device_id"] = config::kDeviceId;
  document["channel"] = reading.channel;
  document["temp_c"] = reading.objectTempC;
  document["ambient_c"] = reading.ambientTempC;
  document["uptime_ms"] = reading.uptimeMs;
  document["sequence"] = reading.sequence;
  document["valid"] = reading.valid;

  char payload[256];
  const size_t length = serializeJson(document, payload, sizeof(payload));
  if (length == 0 || length >= sizeof(payload)) {
    Serial.println("MQTT payload did not fit in buffer");
    return false;
  }

  const bool published =
      mqttClient.publish(config::kPublishTopic, payload, false);
  if (!published) {
    Serial.println("MQTT publish failed");
  }
  return published;
}

void mqttTask(void *parameter) {
  (void)parameter;
  ThermalReading pending{};
  TickType_t lastReconnectAttempt = 0;

  beginWifiConnection();
  while (true) {
    if (WiFi.status() != WL_CONNECTED) {
      if (xTaskGetTickCount() - lastReconnectAttempt >= kReconnectInterval) {
        lastReconnectAttempt = xTaskGetTickCount();
        beginWifiConnection();
      }
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }

    if (!mqttClient.connected()) {
      if (xTaskGetTickCount() - lastReconnectAttempt >= kReconnectInterval) {
        lastReconnectAttempt = xTaskGetTickCount();
        connectMqtt();
      }
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }

    mqttClient.loop();
    if (xQueueReceive(readingQueue, &pending, pdMS_TO_TICKS(100)) == pdTRUE) {
      publishReading(pending);
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(kSdaPin, kSclPin);
  Wire.setClock(100000);
  initialiseSensors();

  readingQueue = xQueueCreate(16, sizeof(ThermalReading));
  if (readingQueue == nullptr) {
    Serial.println("failed to create reading queue");
    while (true) {
      delay(1000);
    }
  }

  mqttClient.setServer(config::kMqttHost, config::kMqttPort);
  mqttClient.setBufferSize(384);

  xTaskCreatePinnedToCore(
      sensorTask,
      "sensor-poll",
      4096,
      nullptr,
      2,
      nullptr,
      1);

  xTaskCreatePinnedToCore(
      mqttTask,
      "mqtt-publish",
      6144,
      nullptr,
      1,
      nullptr,
      0);
}

void loop() {
  vTaskDelay(portMAX_DELAY);
}
