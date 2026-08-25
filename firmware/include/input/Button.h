#pragma once

#include <Arduino.h>

enum class ButtonEvent : uint8_t {
  none,
  shortPress,
  longPress,
};

class Button {
 public:
  explicit Button(uint8_t pin, uint16_t debounceMs = 35,
                  uint16_t longPressMs = 800);

  void begin();
  ButtonEvent update(uint32_t now);

 private:
  uint8_t pin_;
  uint16_t debounceMs_;
  uint16_t longPressMs_;
  bool lastReading_ = HIGH;
  bool stableState_ = HIGH;
  uint32_t changedAt_ = 0;
  uint32_t pressedAt_ = 0;
  bool longPressReported_ = false;
};
