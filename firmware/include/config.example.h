#pragma once

// Copy this file to config.h and replace the placeholders. config.h is ignored
// by Git so local network credentials are not committed.
#define BUDDY_WIFI_SSID "your-wifi-name"
#define BUDDY_WIFI_PASSWORD "your-wifi-password"

// Use the LAN address of the computer running the backend, not 127.0.0.1.
#define BUDDY_SERVER_HOST "192.168.1.100"

namespace buddy::config {

constexpr char deviceId[] = "desk-buddy-esp32";
constexpr uint16_t serverPort = 8000;
constexpr char websocketPath[] = "/ws/device";

// Buttons use INPUT_PULLUP and should connect their GPIO pin to ground.
constexpr uint8_t increaseButtonPin = 25;
constexpr uint8_t decreaseButtonPin = 26;
constexpr uint8_t selectButtonPin = 32;
constexpr uint8_t cancelButtonPin = 27;

}  // namespace buddy::config
