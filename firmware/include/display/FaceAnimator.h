#pragma once

#include <Arduino.h>

enum class IdleEmotion : uint8_t {
  neutral,
  blush,
  winkLeft,
  winkRight,
  delighted,
};

struct FacePose {
  int8_t eyeOffsetX = 0;
  int8_t eyeOffsetY = 0;
  bool blinking = false;
  bool smiling = true;
  IdleEmotion emotion = IdleEmotion::neutral;
};

class FaceAnimator {
 public:
  FacePose idlePose(uint32_t now);

 private:
  uint32_t nextRandom();
  uint32_t randomBetween(uint32_t minimum, uint32_t maximum);
  static bool reached(uint32_t now, uint32_t target);

  uint32_t randomState_ = 0xA17E5EED;
  uint32_t blinkEndsAt_ = 0;
  uint32_t nextBlinkAt_ = 0;
  uint32_t glanceEndsAt_ = 0;
  uint32_t nextGlanceAt_ = 0;
  int8_t glanceOffset_ = 0;
  uint32_t emotionEndsAt_ = 0;
  uint32_t nextEmotionAt_ = 0;
  IdleEmotion emotion_ = IdleEmotion::neutral;
};
