#pragma once

#include <Arduino.h>

constexpr uint8_t PTG_MAX_SENSORS = 8;

struct ThermalReading {
  char sensor_id[16];
  float object_c;
  float ambient_c;
  bool valid;
};

struct TelemetryBatch {
  ThermalReading readings[PTG_MAX_SENSORS];
  uint8_t count;
  uint32_t uptime_s;
  int32_t rssi_dbm;
};
