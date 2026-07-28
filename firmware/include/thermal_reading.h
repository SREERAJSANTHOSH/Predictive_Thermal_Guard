#pragma once

#include <Arduino.h>

struct ThermalReading {
  uint8_t channel;
  float objectTempC;
  float ambientTempC;
  uint32_t uptimeMs;
  uint32_t sequence;
  bool valid;
};

