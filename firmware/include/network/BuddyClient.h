#pragma once

#include <Arduino.h>
#include <WebSocketsClient.h>

using ServerMessageHandler =
    void (*)(const char* messageType, const char* state, uint32_t durationSeconds);

class BuddyClient {
 public:
  BuddyClient(const char* deviceId, ServerMessageHandler onMessage);

  void begin();
  void loop();
  void startTimer(uint32_t durationSeconds);
  void cancelTimer();
  void sendPresence(bool present);
  bool isConnected() const;

 private:
  void handleEvent(WStype_t type, uint8_t* payload, size_t length);
  void sendHandshake();

  const char* deviceId_;
  ServerMessageHandler onMessage_;
  WebSocketsClient websocket_;
  bool connected_ = false;
};
