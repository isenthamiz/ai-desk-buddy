#include "input/Button.h"

Button::Button(uint8_t pin, uint16_t debounceMs, uint16_t longPressMs)
    : pin_(pin), debounceMs_(debounceMs), longPressMs_(longPressMs) {}

void Button::begin() {
  pinMode(pin_, INPUT_PULLUP);
}

ButtonEvent Button::update(uint32_t now) {
  const bool reading = digitalRead(pin_);
  if (reading != lastReading_) {
    lastReading_ = reading;
    changedAt_ = now;
  }

  if (now - changedAt_ < debounceMs_ || reading == stableState_) {
    if (stableState_ == LOW && !longPressReported_ &&
        now - pressedAt_ >= longPressMs_) {
      longPressReported_ = true;
      return ButtonEvent::longPress;
    }
    return ButtonEvent::none;
  }

  stableState_ = reading;
  if (stableState_ == LOW) {
    pressedAt_ = now;
    longPressReported_ = false;
    return ButtonEvent::none;
  }

  return longPressReported_ ? ButtonEvent::none : ButtonEvent::shortPress;
}
