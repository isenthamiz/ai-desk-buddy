#include <Arduino.h>

#include "display/BuddyDisplay.h"
#include "display/Ssd1306Display.h"
#include "input/Button.h"
#include "network/BuddyClient.h"
#include "config.h"

namespace {

constexpr uint8_t kOledAddress = 0x3C;
constexpr uint8_t kSdaPin = 21;
constexpr uint8_t kSclPin = 22;
constexpr uint32_t kFrameIntervalMs = 80;

Ssd1306Display physicalDisplay(kSdaPin, kSclPin, kOledAddress);
BuddyDisplay& buddyDisplay = physicalDisplay;
Button increaseButton(buddy::config::increaseButtonPin);
Button decreaseButton(buddy::config::decreaseButtonPin);
Button selectButton(buddy::config::selectButtonPin);
Button cancelButton(buddy::config::cancelButtonPin);

void handleServerMessage(const char* messageType, const char* state,
                         uint32_t durationSeconds);
BuddyClient buddyClient(buddy::config::deviceId, handleServerMessage);

Face currentFace = Face::idle;
uint32_t lastFrameAt = 0;
constexpr uint32_t kTimerStepSeconds = 10;
constexpr uint32_t kMinimumTimerSeconds = 10;
constexpr uint32_t kMaximumTimerSeconds = 60 * 60;
uint32_t selectedTimerSeconds = 60;
bool selectingTimer = false;
bool timerActive = false;
bool alertActive = false;
bool sleeping = false;
uint32_t timerEndsAt = 0;

void handleServerMessage(const char* messageType, const char* state,
                         uint32_t durationSeconds) {
  if (!strcmp(messageType, "TIMER_STARTED")) {
    timerActive = true;
    alertActive = false;
    selectingTimer = false;
    timerEndsAt = millis() + durationSeconds * 1000UL;
    buddyDisplay.renderTimer(durationSeconds, millis());
    return;
  }
  if (!strcmp(messageType, "TIMER_COMPLETED")) {
    timerActive = false;
    timerEndsAt = 0;
    alertActive = true;
    buddyDisplay.renderAlert(millis());
    return;
  }
  if (!strcmp(messageType, "TIMER_CANCELLED")) {
    timerActive = false;
    alertActive = false;
    timerEndsAt = 0;
    currentFace = Face::idle;
    buddyDisplay.render(currentFace, millis());
    return;
  }
  if (strcmp(messageType, "STATE_CHANGED")) return;

  if (!strcmp(state, "IDLE") && !timerActive && !selectingTimer &&
      !alertActive) {
    sleeping = false;
    currentFace = Face::idle;
  } else if (!strcmp(state, "SLEEPING")) {
    sleeping = true;
    currentFace = Face::sleepy;
  } else if (!strcmp(state, "LISTENING")) {
    currentFace = Face::surprised;
  } else if (!strcmp(state, "THINKING")) {
    currentFace = Face::surprised;
  } else if (!strcmp(state, "SPEAKING")) {
    currentFace = Face::happy;
  } else if (!strcmp(state, "ALERT")) {
    alertActive = true;
    buddyDisplay.renderAlert(millis());
    return;
  } else if (!strcmp(state, "ERROR")) {
    currentFace = Face::error;
  }
  if (!timerActive && !selectingTimer && !alertActive) {
    buddyDisplay.render(currentFace, millis());
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  if (!buddyDisplay.begin()) {
    Serial.println("SSD1306 not found at I2C address 0x3C");
    while (true) {
      delay(1000);
    }
  }

  Serial.println("Face demo started");
  increaseButton.begin();
  decreaseButton.begin();
  selectButton.begin();
  cancelButton.begin();
  buddyClient.begin();
}

void loop() {
  const uint32_t now = millis();
  buddyClient.loop();

  const ButtonEvent increaseEvent = increaseButton.update(now);
  const ButtonEvent decreaseEvent = decreaseButton.update(now);
  const ButtonEvent selectEvent = selectButton.update(now);
  const ButtonEvent cancelEvent = cancelButton.update(now);

  if (increaseEvent == ButtonEvent::shortPress && !timerActive && !alertActive &&
      !sleeping) {
    selectingTimer = true;
    if (selectedTimerSeconds <= kMaximumTimerSeconds - kTimerStepSeconds) {
      selectedTimerSeconds += kTimerStepSeconds;
    }
    buddyDisplay.renderTimerSelection(selectedTimerSeconds);
    Serial.printf("Selected timer: %lu seconds\n", selectedTimerSeconds);
  }

  if (decreaseEvent == ButtonEvent::shortPress && !timerActive && !alertActive &&
      !sleeping) {
    selectingTimer = true;
    if (selectedTimerSeconds >= kMinimumTimerSeconds + kTimerStepSeconds) {
      selectedTimerSeconds -= kTimerStepSeconds;
    }
    buddyDisplay.renderTimerSelection(selectedTimerSeconds);
    Serial.printf("Selected timer: %lu seconds\n", selectedTimerSeconds);
  }

  if (selectEvent == ButtonEvent::shortPress ||
      selectEvent == ButtonEvent::longPress) {
    if (alertActive) {
      alertActive = false;
      currentFace = Face::idle;
      buddyDisplay.render(currentFace, now);
      Serial.println("Alert acknowledged with Select");
    } else if (timerActive) {
      Serial.println("Select pressed: cancelling active timer");
      buddyClient.cancelTimer();
    } else if (selectingTimer) {
      Serial.printf("Select pressed: starting %lu second timer\n",
                    selectedTimerSeconds);
      buddyClient.startTimer(selectedTimerSeconds);
    } else {
      Serial.printf("Select pressed: requesting %s\n",
                    sleeping ? "wake" : "sleep");
      buddyClient.sendPresence(sleeping);
    }
  }

  if (cancelEvent == ButtonEvent::shortPress) {
    if (alertActive) {
      alertActive = false;
      currentFace = Face::idle;
      buddyDisplay.render(currentFace, now);
      Serial.println("Alert dismissed");
    } else if (timerActive) {
      buddyClient.cancelTimer();
    } else if (selectingTimer) {
      selectingTimer = false;
      currentFace = Face::idle;
      buddyDisplay.render(currentFace, now);
      Serial.println("Timer selection dismissed");
    }
  }

  if (now - lastFrameAt >= kFrameIntervalMs) {
    lastFrameAt = now;
    if (alertActive) {
      buddyDisplay.renderAlert(now);
    } else if (timerActive) {
      const uint32_t remaining =
          timerEndsAt > now ? (timerEndsAt - now + 999) / 1000 : 0;
      buddyDisplay.renderTimer(remaining, now);
    } else if (!selectingTimer) {
      buddyDisplay.render(currentFace, now);
    }
  }
}
