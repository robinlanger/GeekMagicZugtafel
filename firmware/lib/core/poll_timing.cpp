#include "poll_timing.h"

namespace gb {

uint32_t nextDelayMs(bool ok, int nextInHeader, uint8_t consecutiveFailures) {
  if (ok) {
    if (nextInHeader < 0) return 10000;
    int s = nextInHeader < 2 ? 2 : (nextInHeader > 30 ? 30 : nextInHeader);
    return static_cast<uint32_t>(s) * 1000u;
  }
  // Exponential backoff: 2 s, 4 s, 8 s ... capped at 30 s.
  uint32_t shift = consecutiveFailures == 0 ? 0 : consecutiveFailures - 1u;
  if (shift >= 4) return 30000;  // 2000 << 4 = 32000 > cap
  uint32_t d = 2000u << shift;
  return d > 30000u ? 30000u : d;
}

bool showOffline(uint32_t msSinceLastSuccess) { return msSinceLastSuccess >= 120000; }

bool acceptFrameLength(int32_t contentLength) {
  return contentLength > 0 && contentLength <= kMaxFrameBytes;
}

}  // namespace gb
