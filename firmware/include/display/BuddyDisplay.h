#pragma once

#include <Arduino.h>

enum class Face : uint8_t {
  idle,
  happy,
  sleepy,
  surprised,
  error,
};

class BuddyDisplay {
 public:
  virtual ~BuddyDisplay() = default;

  virtual bool begin() = 0;
  virtual void render(Face face, uint32_t now) = 0;
  virtual void renderTimerSelection(uint32_t seconds) = 0;
  virtual void renderTimer(uint32_t remainingSeconds, uint32_t now) = 0;
  virtual void renderAlert(uint32_t now) = 0;
};
