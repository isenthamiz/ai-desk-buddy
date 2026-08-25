#include "display/Ssd1306Display.h"

#include <Adafruit_GFX.h>
#include <Wire.h>

namespace {

constexpr uint8_t kScreenWidth = 128;
constexpr uint8_t kScreenHeight = 64;

}  // namespace

Ssd1306Display::Ssd1306Display(uint8_t sdaPin, uint8_t sclPin, uint8_t address)
    : sdaPin_(sdaPin),
      sclPin_(sclPin),
      address_(address),
      display_(kScreenWidth, kScreenHeight, &Wire, -1) {}

bool Ssd1306Display::begin() {
  Wire.begin(sdaPin_, sclPin_);
  if (!display_.begin(SSD1306_SWITCHCAPVCC, address_)) {
    return false;
  }

  display_.setTextColor(SSD1306_WHITE);
  display_.clearDisplay();
  display_.display();
  return true;
}

void Ssd1306Display::render(Face face, uint32_t now) {
  display_.clearDisplay();

  switch (face) {
    case Face::idle:
      drawIdle(now);
      break;
    case Face::happy:
      drawHappy();
      break;
    case Face::sleepy:
      drawSleepy(now);
      break;
    case Face::surprised:
      drawSurprised(now);
      break;
    case Face::error:
      drawError(now);
      break;
  }

  display_.display();
}

void Ssd1306Display::renderTimerSelection(uint32_t seconds) {
  display_.clearDisplay();
  display_.fillRoundRect(37, 3, 10, 17, 4, SSD1306_WHITE);
  display_.fillRoundRect(81, 3, 10, 17, 4, SSD1306_WHITE);
  display_.drawPixel(60, 19, SSD1306_WHITE);
  display_.drawLine(61, 20, 63, 21, SSD1306_WHITE);
  display_.drawLine(64, 21, 66, 20, SSD1306_WHITE);
  display_.drawPixel(67, 19, SSD1306_WHITE);
  display_.fillCircle(115, 8, 2, SSD1306_WHITE);
  display_.setTextSize(1);
  display_.setCursor(41, 27);
  display_.print("SET TIMER");
  char duration[8];
  snprintf(duration, sizeof(duration), "%02lu:%02lu", seconds / 60,
           seconds % 60);
  display_.setTextSize(2);
  display_.setCursor(34, 43);
  display_.print(duration);
  display_.display();
}

void Ssd1306Display::renderTimer(uint32_t remainingSeconds, uint32_t now) {
  display_.clearDisplay();

  const bool blinking = now % 3200 < 160;
  if (blinking) {
    display_.drawLine(34, 19, 49, 19, SSD1306_WHITE);
    display_.drawLine(79, 19, 94, 19, SSD1306_WHITE);
  } else {
    const int8_t leftBob = (now / 350) % 3;
    const int8_t rightBob = 2 - leftBob;
    display_.fillRoundRect(35, 7 + leftBob, 13, 25, 5, SSD1306_WHITE);
    display_.fillRoundRect(80, 7 + rightBob, 13, 25, 5, SSD1306_WHITE);
  }

  const uint8_t activeDot = (now / 250) % 3;
  for (uint8_t dot = 0; dot < 3; ++dot) {
    const uint8_t radius = dot == activeDot ? 3 : 1;
    display_.fillCircle(57 + dot * 7, 34, radius, SSD1306_WHITE);
  }
  display_.fillCircle(115, 8, 2, SSD1306_WHITE);

  const uint32_t minutes = remainingSeconds / 60;
  const uint32_t seconds = remainingSeconds % 60;
  char countdown[8];
  snprintf(countdown, sizeof(countdown), "%02lu:%02lu", minutes, seconds);
  display_.setTextSize(2);
  display_.setCursor(34, 46);
  display_.print(countdown);
  display_.setTextSize(1);
  display_.display();
}

void Ssd1306Display::renderAlert(uint32_t now) {
  display_.clearDisplay();
  const bool flash = (now / 300) % 2 == 0;
  if (flash) {
    display_.fillCircle(8, 8, 3, SSD1306_WHITE);
    display_.fillCircle(120, 8, 3, SSD1306_WHITE);
    display_.fillCircle(8, 56, 3, SSD1306_WHITE);
    display_.fillCircle(120, 56, 3, SSD1306_WHITE);
  }

  const int8_t bounce = (now / 180) % 2;
  display_.fillRoundRect(35, 5 + bounce, 13, 27, 5, SSD1306_WHITE);
  display_.fillRoundRect(80, 6 - bounce, 13, 27, 5, SSD1306_WHITE);
  display_.drawCircle(64, 34, 3, SSD1306_WHITE);
  display_.setTextSize(2);
  display_.setCursor(16, 46);
  display_.print("TIME UP!");
  display_.setTextSize(1);
  display_.display();
}

void Ssd1306Display::drawOpenEyes(int8_t y) {
  display_.fillRoundRect(35, y, 13, 30, 5, SSD1306_WHITE);
  display_.fillRoundRect(80, y, 13, 30, 5, SSD1306_WHITE);
}

void Ssd1306Display::drawClosedEyes() {
  display_.drawLine(34, 31, 49, 31, SSD1306_WHITE);
  display_.drawLine(79, 31, 94, 31, SSD1306_WHITE);
}

void Ssd1306Display::drawIdle(uint32_t now) {
  const FacePose pose = animator_.idlePose(now);
  const int8_t leftX = 35 + pose.eyeOffsetX;
  const int8_t rightX = 80 + pose.eyeOffsetX;
  const int8_t eyeY = 14 + pose.eyeOffsetY;

  if (pose.emotion == IdleEmotion::delighted) {
    display_.drawLine(leftX - 1, 30, leftX + 6, 23, SSD1306_WHITE);
    display_.drawLine(leftX + 6, 23, leftX + 14, 30, SSD1306_WHITE);
    display_.drawLine(rightX - 1, 30, rightX + 6, 23, SSD1306_WHITE);
    display_.drawLine(rightX + 6, 23, rightX + 14, 30, SSD1306_WHITE);
  } else if (pose.emotion == IdleEmotion::winkLeft) {
    display_.drawLine(leftX - 1, 31, leftX + 14, 31, SSD1306_WHITE);
    display_.fillRoundRect(rightX, eyeY, 13, 30, 5, SSD1306_WHITE);
  } else if (pose.emotion == IdleEmotion::winkRight) {
    display_.fillRoundRect(leftX, eyeY, 13, 30, 5, SSD1306_WHITE);
    display_.drawLine(rightX - 1, 31, rightX + 14, 31, SSD1306_WHITE);
  } else if (pose.blinking) {
    display_.drawLine(34 + pose.eyeOffsetX, 31, 49 + pose.eyeOffsetX, 31,
                      SSD1306_WHITE);
    display_.drawLine(79 + pose.eyeOffsetX, 31, 94 + pose.eyeOffsetX, 31,
                      SSD1306_WHITE);
  } else {
    const uint8_t eyeHeight = pose.emotion == IdleEmotion::blush ? 25 : 30;
    display_.fillRoundRect(leftX, eyeY, 13, eyeHeight, 5, SSD1306_WHITE);
    display_.fillRoundRect(rightX, eyeY, 13, eyeHeight, 5, SSD1306_WHITE);
  }

  if (pose.smiling) {
    display_.drawPixel(59, 49, SSD1306_WHITE);
    display_.drawLine(60, 50, 63, 52, SSD1306_WHITE);
    display_.drawLine(64, 52, 67, 50, SSD1306_WHITE);
    display_.drawPixel(68, 49, SSD1306_WHITE);
  } else {
    display_.drawLine(60, 51, 68, 51, SSD1306_WHITE);
  }

  if (pose.emotion == IdleEmotion::blush) {
    for (uint8_t offset = 0; offset < 3; ++offset) {
      display_.drawLine(20 + offset * 4, 44, 22 + offset * 4, 42,
                        SSD1306_WHITE);
      display_.drawLine(98 + offset * 4, 42, 100 + offset * 4, 44,
                        SSD1306_WHITE);
    }
  } else if (pose.emotion == IdleEmotion::winkLeft ||
             pose.emotion == IdleEmotion::winkRight) {
    display_.drawLine(109, 15, 117, 15, SSD1306_WHITE);
    display_.drawLine(113, 11, 113, 19, SSD1306_WHITE);
    display_.drawPixel(110, 12, SSD1306_WHITE);
    display_.drawPixel(116, 18, SSD1306_WHITE);
  }
  display_.fillCircle(115, 8, 2, SSD1306_WHITE);
}

void Ssd1306Display::drawHappy() {
  display_.drawLine(34, 28, 41, 22, SSD1306_WHITE);
  display_.drawLine(41, 22, 49, 28, SSD1306_WHITE);
  display_.drawLine(79, 28, 86, 22, SSD1306_WHITE);
  display_.drawLine(86, 22, 94, 28, SSD1306_WHITE);
  display_.drawLine(55, 45, 63, 50, SSD1306_WHITE);
  display_.drawLine(64, 50, 73, 45, SSD1306_WHITE);
  display_.fillCircle(115, 8, 2, SSD1306_WHITE);
}

void Ssd1306Display::drawSleepy(uint32_t now) {
  drawClosedEyes();
  display_.drawCircle(64, 50, 3, SSD1306_WHITE);
  display_.setTextSize(1);
  display_.setCursor(104, 10 + ((now / 500) % 4));
  display_.print("z");
  display_.setCursor(113, 3);
  display_.print("Z");
  display_.drawPixel(115, 8, SSD1306_WHITE);
}

void Ssd1306Display::drawSurprised(uint32_t now) {
  const int8_t bob = (now / 250) % 2;
  display_.fillRoundRect(34, 10 + bob, 15, 34, 6, SSD1306_WHITE);
  display_.fillRoundRect(79, 10 + bob, 15, 34, 6, SSD1306_WHITE);
  display_.drawCircle(64, 52, 4, SSD1306_WHITE);
  display_.fillCircle(115, 8, 2, SSD1306_WHITE);
}

void Ssd1306Display::drawError(uint32_t now) {
  const int8_t shake = static_cast<int8_t>((now / 120) % 3) - 1;
  display_.drawLine(34 + shake, 17, 49 + shake, 38, SSD1306_WHITE);
  display_.drawLine(49 + shake, 17, 34 + shake, 38, SSD1306_WHITE);
  display_.drawLine(79 + shake, 17, 94 + shake, 38, SSD1306_WHITE);
  display_.drawLine(94 + shake, 17, 79 + shake, 38, SSD1306_WHITE);
  display_.drawLine(59, 51, 69, 51, SSD1306_WHITE);
  if ((now / 300) % 2 == 0) {
    display_.fillCircle(115, 8, 2, SSD1306_WHITE);
  }
}
