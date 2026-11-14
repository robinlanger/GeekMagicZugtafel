#include "boot_guard.h"

namespace gb {

BootDecision onBoot(BootState rtc) {
  if (rtc.magic != kBootMagic) {
    return {{kBootMagic, 1}, false};
  }
  bool safe = rtc.failed >= kSafeModeThreshold;
  uint8_t next = rtc.failed == 255 ? 255 : static_cast<uint8_t>(rtc.failed + 1);
  return {{kBootMagic, next}, safe};
}

BootState markHealthy() { return {kBootMagic, 0}; }

bool isHealthy(uint32_t uptimeMs, bool wifi, bool web) {
  return uptimeMs >= kHealthyUptimeMs && wifi && web;
}

}  // namespace gb
