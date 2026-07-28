#include <Adafruit_MLX90614.h>
#include <Arduino.h>
#include <Wire.h>

#include "thermal_reading.h"

namespace {

constexpr uint8_t kMuxAddress = 0x70;
constexpr uint8_t kSdaPin = 21;
constexpr uint8_t kSclPin = 22;
constexpr uint8_t kSensorChannels[] = {0, 1, 2, 3};
constexpr TickType_t kPollInterval = pdMS_TO_TICKS(1000);

Adafruit_MLX90614 sensors[4];
bool sensorAvailable[4] = {false, false, false, false};
uint32_t sequenceNumber = 0;

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
    }

    disableMuxChannels();
    vTaskDelayUntil(&lastWakeTime, kPollInterval);
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(kSdaPin, kSclPin);
  Wire.setClock(100000);
  initialiseSensors();

  xTaskCreatePinnedToCore(
      sensorTask,
      "sensor-poll",
      4096,
      nullptr,
      2,
      nullptr,
      1);
}

void loop() {
  vTaskDelay(portMAX_DELAY);
}
