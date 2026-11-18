#pragma once
#include <cstdint>
#include <string>

#include "settings.h"

namespace gb {

// Night mode (spec 2026-11-15-nachtmodus-design.md). Hardware-free so it runs in native tests.

// "HH:MM:SS" (exactly, 24 h) -> seconds of the day 0..86399; anything else (or nullptr) -> -1.
int32_t parseLocalTime(const char* s);
// "HH:MM" (exactly, 24 h) -> minutes of the day 0..1439; anything else (or nullptr) -> -1.
int parseHhMm(const char* s);
// Minutes of the day -> "HH:MM".
std::string formatHhMm(uint16_t minutes);

// Wall clock synced from the server's X-Local-Time and carried on with millis().
// Unsigned arithmetic keeps it correct across the 49.7-day millis() wrap.
class LocalClock {
 public:
  void sync(uint32_t secOfDay, uint32_t nowMs);
  bool known() const { return known_; }
  // Only meaningful when known().
  uint32_t secondOfDay(uint32_t nowMs) const;

 private:
  bool known_ = false;
  uint32_t syncSec_ = 0;
  uint32_t syncMs_ = 0;
};

// Night window [start, end) in minutes; start > end wraps past midnight; start == end is off.
bool nightActive(uint16_t start, uint16_t end, uint16_t minuteOfDay);
// Backlight percentage to apply now: night brightness inside the window (time known), else day.
uint8_t effectiveBrightness(const Settings& s, bool timeKnown, uint32_t secondOfDay);

// PWM range used for the backlight (analogWriteRange): fine enough for the dark end.
constexpr uint16_t kBacklightPwmRange = 1000;
// Backlight percentage -> PWM on-time out of kBacklightPwmRange. Quadratic, because the eye
// sees a linear duty as barely dimming (20 % duty looks about half as bright). 0 stays off,
// any other value is at least 1 so the backlight never goes out by rounding.
uint16_t backlightDuty(uint8_t pct);

// Live preview from the web page's sliders: overrides the backlight until no new preview
// arrived for kPreviewHoldMs. Never saved. Unsigned arithmetic survives the millis() wrap.
constexpr uint32_t kPreviewHoldMs = 3000;
class BacklightPreview {
 public:
  void set(uint8_t pct, uint32_t nowMs);  // pct clamped to 0..100
  void clear() { set_ = false; }
  bool active(uint32_t nowMs) const { return set_ && nowMs - lastMs_ < kPreviewHoldMs; }
  uint8_t pct() const { return pct_; }

 private:
  bool set_ = false;
  uint8_t pct_ = 0;
  uint32_t lastMs_ = 0;
};

// Validate the web form values ("HH:MM", "HH:MM", "0".."100") into s. On failure *error is
// "bad_time" or "bad_night_brightness" and s is unchanged.
bool applyNight(Settings& s, const std::string& start, const std::string& end,
                const std::string& brightness, std::string* error);

}  // namespace gb
