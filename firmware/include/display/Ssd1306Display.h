#pragma once

#include <Adafruit_SSD1306.h>

#include "display/BuddyDisplay.h"
#include "display/FaceAnimator.h"

class Ssd1306Display final : public BuddyDisplay {
 public:
  Ssd1306Display(uint8_t sdaPin, uint8_t sclPin, uint8_t address);

  bool begin() override;
  void render(Face face, uint32_t now) override;
  void renderTimerSelection(uint32_t seconds) override;
  void renderTimer(uint32_t remainingSeconds, uint32_t now) override;
  void renderAlert(uint32_t now) override;

 private:
  void drawOpenEyes(int8_t y = 22);
  void drawClosedEyes();
  void drawIdle(uint32_t now);
  void drawHappy();
  void drawSleepy(uint32_t now);
  void drawSurprised(uint32_t now);
  void drawError(uint32_t now);

  uint8_t sdaPin_;
  uint8_t sclPin_;
  uint8_t address_;
  Adafruit_SSD1306 display_;
  FaceAnimator animator_;
};
