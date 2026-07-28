#pragma once

// Lab-network settings. Replace these values before flashing the board.
// Keep real passwords out of version control.
namespace config {

constexpr char kWifiSsid[] = "YOUR_WIFI_SSID";
constexpr char kWifiPassword[] = "YOUR_WIFI_PASSWORD";
constexpr char kMqttHost[] = "192.168.1.10";
constexpr uint16_t kMqttPort = 1883;
constexpr char kDeviceId[] = "panel-a";
constexpr char kPublishTopic[] = "thermal-fault-guard/panel-a/temperature";

}  // namespace config
