// Thermal Symmetry Guard — ESP32 application layer.
//
// Reads a multiplexed array of MLX90614 IR sensors plus one ambient sensor,
// feeds them to the symmetry core, and publishes verdicts. There is no
// calibration wizard, no emissivity table and no contact probe, because the
// core does not need any of them.

#include <Arduino.h>
#include <Wire.h>

extern "C" {
#include "symmetry.h"
}

namespace {

constexpr uint8_t  kMuxAddr      = 0x70;   // TCA9548A
constexpr uint8_t  kMlxAddr      = 0x5A;
constexpr uint8_t  kPointCount   = 3;
constexpr uint32_t kSweepMs      = 4000;   // 0.25 Hz: slow is fine, heat is slow
constexpr const char *kPointIds[kPointCount] = {"L1", "L2", "L3"};

tsg_group_t  g_group;
tsg_result_t g_results[TSG_MAX_POINTS];

void muxSelect(uint8_t channel) {
    Wire.beginTransmission(kMuxAddr);
    Wire.write(static_cast<uint8_t>(1 << channel));
    Wire.endTransmission();
}

// Raw object temperature, straight off the sensor. The emissivity register is
// left at its factory value on purpose: the core cancels it, and writing it
// would only wear the EEPROM.
bool readMlxObject(uint8_t channel, float &out_c) {
    muxSelect(channel);
    Wire.beginTransmission(kMlxAddr);
    Wire.write(0x07);                       // RAM 0x07 = T_obj1
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(kMlxAddr, static_cast<uint8_t>(3)) != 3) return false;

    const uint8_t lo  = Wire.read();
    const uint8_t hi  = Wire.read();
    Wire.read();                            // PEC, ignored
    const uint16_t raw = static_cast<uint16_t>((hi << 8) | lo);
    if (hi & 0x80) return false;            // error flag
    out_c = raw * 0.02f - 273.15f;
    return out_c > -60.0f && out_c < 400.0f;
}

bool readAmbient(float &out_c) {
    // MLX90614 ambient (RAM 0x06) on channel 0 doubles as the reference.
    muxSelect(0);
    Wire.beginTransmission(kMlxAddr);
    Wire.write(0x06);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(kMlxAddr, static_cast<uint8_t>(3)) != 3) return false;
    const uint8_t lo = Wire.read();
    const uint8_t hi = Wire.read();
    Wire.read();
    out_c = static_cast<uint16_t>((hi << 8) | lo) * 0.02f - 273.15f;
    return out_c > -60.0f && out_c < 150.0f;
}

}  // namespace

void setup() {
    Serial.begin(115200);
    Wire.begin();
    Wire.setClock(100000);

    tsg_group_init(&g_group, 3.5f);
    for (uint8_t i = 0; i < kPointCount; i++) {
        tsg_group_add(&g_group, kPointIds[i]);
    }

    Serial.println(F("Thermal Symmetry Guard"));
    Serial.println(F("Commissioning: learning per-point offsets."));
    Serial.println(F("Keep the equipment in normal service. No probes needed."));
}

void loop() {
    static uint32_t next_ms = 0;
    const uint32_t now = millis();
    if (static_cast<int32_t>(now - next_ms) < 0) return;
    next_ms = now + kSweepMs;

    float ambient_c = 0.0f;
    if (!readAmbient(ambient_c)) {
        Serial.println(F("ambient read failed; skipping sweep"));
        return;
    }

    float temps[TSG_MAX_POINTS] = {0};
    bool  present[TSG_MAX_POINTS] = {false};
    for (uint8_t i = 0; i < kPointCount; i++) {
        present[i] = readMlxObject(i, temps[i]);
    }

    tsg_group_update(&g_group, temps, present, ambient_c,
                     now / 1000.0f, g_results);

    for (uint8_t i = 0; i < kPointCount; i++) {
        const tsg_result_t &r = g_results[i];
        Serial.printf("%-4s %6.1fC rise %5.1fK z=%+6.2f cusum=%+7.1f  %s\n",
                      kPointIds[i], r.temp_c, r.rise_k, r.z, r.cusum,
                      tsg_verdict_name(r.verdict));
    }
    Serial.println();
}
