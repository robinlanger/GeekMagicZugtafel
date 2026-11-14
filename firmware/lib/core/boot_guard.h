#pragma once
#include <cstdint>

namespace gb {

constexpr uint32_t kBootMagic = 0x47424F58;  // "GBOX"
constexpr uint8_t kSafeModeThreshold = 3;
constexpr uint32_t kHealthyUptimeMs = 60000;

struct BootState {
  uint32_t magic;
  uint8_t failed;
};

struct BootDecision {
  BootState next;
  bool safeMode;
};

BootDecision onBoot(BootState rtc);
BootState markHealthy();
bool isHealthy(uint32_t uptimeMs, bool wifi, bool web);

// Latches the first healthy moment of a boot: shouldMark() returns true exactly once,
// so markHealthy() is written to RTC memory once per boot.
class HealthLatch {
 public:
  bool shouldMark(uint32_t uptimeMs, bool wifi, bool web);
  bool marked() const { return marked_; }

 private:
  bool marked_ = false;
};

}  // namespace gb
