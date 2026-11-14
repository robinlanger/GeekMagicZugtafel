#pragma once
// Boot-guard state in RTC user memory (survives soft resets and OTA reboots).
// Shared by the OTA handler (writes markHealthy) and setup()'s boot guard.
#include <Arduino.h>

#include "boot_guard.h"

// Offset in 4-byte blocks into RTC *user* memory. Blocks 0..31 hold the eboot
// command that stages an OTA image, so stay well clear of them.
constexpr uint32_t kRtcBootSlot = 64;

inline gb::BootState rtcBootRead() {
  uint32_t w[2] = {0, 0};
  ESP.rtcUserMemoryRead(kRtcBootSlot, w, sizeof(w));
  return {w[0], static_cast<uint8_t>(w[1])};
}

inline void rtcBootWrite(const gb::BootState& s) {
  uint32_t w[2] = {s.magic, s.failed};
  ESP.rtcUserMemoryWrite(kRtcBootSlot, w, sizeof(w));
}
