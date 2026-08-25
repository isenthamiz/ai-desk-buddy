#include "network/BuddyClient.h"

#include <ArduinoJson.h>
#include <WiFi.h>

#include "config.h"

BuddyClient::BuddyClient(const char* deviceId, ServerMessageHandler onMessage)
    : deviceId_(deviceId), onMessage_(onMessage) {}

void BuddyClient::begin() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(BUDDY_WIFI_SSID, BUDDY_WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print('.');
  }
  Serial.print("\nESP32 IP: ");
  Serial.println(WiFi.localIP());

  websocket_.begin(BUDDY_SERVER_HOST, buddy::config::serverPort,
                   buddy::config::websocketPath);
  websocket_.onEvent(
      [this](WStype_t type, uint8_t* payload, size_t length) {
        handleEvent(type, payload, length);
      });
  websocket_.setReconnectInterval(3000);
}

void BuddyClient::loop() {
  websocket_.loop();
}

void BuddyClient::startTimer(uint32_t durationSeconds) {
  if (!connected_) {
    Serial.println("Button ignored: server is not connected");
    return;
  }

  JsonDocument message;
  message["type"] = "BUTTON_PRESSED";
  message["button"] = "TIMER_START";
  message["durationSeconds"] = durationSeconds;
  String payload;
  serializeJson(message, payload);
  websocket_.sendTXT(payload);
  Serial.printf("Requested timer: %lu seconds\n", durationSeconds);
}

void BuddyClient::cancelTimer() {
  if (!connected_) {
    Serial.println("Button ignored: server is not connected");
    return;
  }
  JsonDocument message;
  message["type"] = "BUTTON_PRESSED";
  message["button"] = "TIMER_CANCEL";
  String payload;
  serializeJson(message, payload);
  websocket_.sendTXT(payload);
  Serial.println("Requested timer cancellation");
}

void BuddyClient::sendPresence(bool present) {
  if (!connected_) {
    Serial.println("Button ignored: server is not connected");
    return;
  }
  JsonDocument message;
  message["type"] = "PRESENCE_CHANGED";
  message["present"] = present;
  String payload;
  serializeJson(message, payload);
  websocket_.sendTXT(payload);
  Serial.printf("Requested state: %s\n", present ? "awake" : "sleeping");
}

bool BuddyClient::isConnected() const {
  return connected_;
}

void BuddyClient::handleEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) {
    connected_ = true;
    Serial.println("WebSocket connected");
    sendHandshake();
    return;
  }

  if (type == WStype_DISCONNECTED) {
    connected_ = false;
    Serial.println("WebSocket disconnected");
    return;
  }

  if (type != WStype_TEXT) {
    return;
  }

  JsonDocument message;
  if (deserializeJson(message, payload, length)) {
    Serial.println("Invalid server JSON");
    return;
  }

  const char* messageType = message["type"] | "";
  if (!strcmp(messageType, "STATE_CHANGED")) {
    const char* state = message["state"] | "IDLE";
    Serial.printf("Received state: %s\n", state);
    onMessage_(messageType, state, 0);
  } else if (!strcmp(messageType, "TIMER_STARTED")) {
    const uint32_t duration = message["durationSeconds"] | 0UL;
    Serial.printf("Timer confirmed: %lu seconds\n", duration);
    onMessage_(messageType, "", duration);
  } else if (!strcmp(messageType, "TIMER_CANCELLED") ||
             !strcmp(messageType, "TIMER_COMPLETED")) {
    Serial.printf("Received: %s\n", messageType);
    onMessage_(messageType, "", 0);
  }
}

void BuddyClient::sendHandshake() {
  JsonDocument message;
  message["type"] = "DEVICE_CONNECTED";
  message["deviceId"] = deviceId_;
  message["deviceType"] = "ESP32";
  String payload;
  serializeJson(message, payload);
  websocket_.sendTXT(payload);
}
