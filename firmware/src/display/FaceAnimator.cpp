#include "display/FaceAnimator.h"

FacePose FaceAnimator::idlePose(uint32_t now) {
  if (nextBlinkAt_ == 0) {
    nextBlinkAt_ = now + randomBetween(1800, 4200);
    nextGlanceAt_ = now + randomBetween(2400, 5200);
    nextEmotionAt_ = now + randomBetween(4000, 7500);
  }

  if (reached(now, nextBlinkAt_)) {
    blinkEndsAt_ = now + randomBetween(110, 180);
    nextBlinkAt_ = blinkEndsAt_ + randomBetween(1800, 4500);
  }

  if (reached(now, nextGlanceAt_)) {
    glanceOffset_ = (nextRandom() & 1U) == 0 ? -3 : 3;
    glanceEndsAt_ = now + randomBetween(500, 1000);
    nextGlanceAt_ = glanceEndsAt_ + randomBetween(2200, 5200);
  }

  if (glanceOffset_ != 0 && reached(now, glanceEndsAt_)) {
    glanceOffset_ = 0;
  }

  if (emotion_ == IdleEmotion::neutral && reached(now, nextEmotionAt_)) {
    emotion_ = static_cast<IdleEmotion>(1 + nextRandom() % 4);
    emotionEndsAt_ = now + randomBetween(850, 1500);
  } else if (emotion_ != IdleEmotion::neutral && reached(now, emotionEndsAt_)) {
    emotion_ = IdleEmotion::neutral;
    nextEmotionAt_ = now + randomBetween(4500, 9000);
  }

  FacePose pose;
  pose.blinking = emotion_ == IdleEmotion::neutral && blinkEndsAt_ != 0 &&
                  !reached(now, blinkEndsAt_);
  pose.eyeOffsetX = glanceOffset_;
  pose.eyeOffsetY = static_cast<int8_t>((now / 700) % 2);
  pose.smiling = emotion_ != IdleEmotion::neutral || glanceOffset_ == 0 ||
                 (now / 220) % 2 == 0;
  pose.emotion = emotion_;
  return pose;
}

uint32_t FaceAnimator::nextRandom() {
  randomState_ = randomState_ * 1664525UL + 1013904223UL;
  return randomState_;
}

uint32_t FaceAnimator::randomBetween(uint32_t minimum, uint32_t maximum) {
  return minimum + nextRandom() % (maximum - minimum + 1);
}

bool FaceAnimator::reached(uint32_t now, uint32_t target) {
  return static_cast<int32_t>(now - target) >= 0;
}
