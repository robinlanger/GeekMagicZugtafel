#include "night.h"

#include <cstdio>

namespace gb {

namespace {

constexpr uint32_t kSecPerDay = 86400;

// Two decimal digits at s[0..1] -> 0..99, or -1.
int twoDigits(const char* s) {
  if (s[0] < '0' || s[0] > '9' || s[1] < '0' || s[1] > '9') return -1;
  return (s[0] - '0') * 10 + (s[1] - '0');
}

// Parses "HH:MM" or "HH:MM:SS" (fields = 2 or 3) of exactly that length into seconds.
int32_t parseClock(const char* s, int fields) {
  if (s == nullptr) return -1;
  const size_t len = static_cast<size_t>(fields) * 3 - 1;
  for (size_t i = 0; i < len; ++i) {
    if (s[i] == '\0') return -1;
  }
  if (s[len] != '\0') return -1;
  const int limits[3] = {23, 59, 59};
  int32_t total = 0;
  for (int f = 0; f < fields; ++f) {
    const char* p = s + f * 3;
    if (f > 0 && s[f * 3 - 1] != ':') return -1;
    const int v = twoDigits(p);
    if (v < 0 || v > limits[f]) return -1;
    total = total * 60 + v;
  }
  return fields == 2 ? total * 60 : total;
}

}  // namespace

int32_t parseLocalTime(const char* s) { return parseClock(s, 3); }

int parseHhMm(const char* s) {
  const int32_t sec = parseClock(s, 2);
  return sec < 0 ? -1 : static_cast<int>(sec / 60);
}

std::string formatHhMm(uint16_t minutes) {
  char buf[6];
  std::snprintf(buf, sizeof(buf), "%02u:%02u", static_cast<unsigned>(minutes / 60) % 24,
                static_cast<unsigned>(minutes % 60));
  return buf;
}

void LocalClock::sync(uint32_t secOfDay, uint32_t nowMs) {
  known_ = true;
  syncSec_ = secOfDay % kSecPerDay;
  syncMs_ = nowMs;
}

uint32_t LocalClock::secondOfDay(uint32_t nowMs) const {
  const uint32_t elapsedSec = (nowMs - syncMs_) / 1000;
  return (syncSec_ + elapsedSec % kSecPerDay) % kSecPerDay;
}

bool nightActive(uint16_t start, uint16_t end, uint16_t minuteOfDay) {
  if (start == end) return false;
  if (start < end) return minuteOfDay >= start && minuteOfDay < end;
  return minuteOfDay >= start || minuteOfDay < end;
}

uint8_t effectiveBrightness(const Settings& s, bool timeKnown, uint32_t secondOfDay) {
  if (timeKnown &&
      nightActive(s.nightStart, s.nightEnd, static_cast<uint16_t>(secondOfDay / 60))) {
    return s.nightBrightness;
  }
  return s.brightness;
}

bool applyNight(Settings& s, const std::string& start, const std::string& end,
                const std::string& brightness, std::string* error) {
  const int a = parseHhMm(start.c_str());
  const int b = parseHhMm(end.c_str());
  if (a < 0 || b < 0) {
    if (error) *error = "bad_time";
    return false;
  }
  int pct = 0;
  bool ok = !brightness.empty() && brightness.size() <= 3;
  for (char c : brightness) {
    if (c < '0' || c > '9') ok = false;
    else pct = pct * 10 + (c - '0');
  }
  if (!ok || pct > 100) {
    if (error) *error = "bad_night_brightness";
    return false;
  }
  s.nightStart = static_cast<uint16_t>(a);
  s.nightEnd = static_cast<uint16_t>(b);
  s.nightBrightness = static_cast<uint8_t>(pct);
  return true;
}

}  // namespace gb
