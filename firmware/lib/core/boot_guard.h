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

// Why the chip started. Fresh: power-on or reset pin; RTC memory may still hold an old
// count (it can survive a brief power loss), but the user asked for a clean start.
// Counted: crash, watchdog, software restart (OTA, /restart) and anything unknown.
enum class ResetKind : uint8_t { Fresh, Counted };

// Raw values of the SDK's rst_reason (user_interface.h); main.cpp static_asserts them.
constexpr uint32_t kResetReasonPowerOn = 0;   // REASON_DEFAULT_RST
constexpr uint32_t kResetReasonExtPin = 6;    // REASON_EXT_SYS_RST

ResetKind resetKindFromReason(uint32_t reason);

// Fresh start: counter begins at 1, never safe mode. Counted: increments, safe mode
// once kSafeModeThreshold boots in a row failed.
BootDecision onBoot(BootState rtc, ResetKind kind);
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
