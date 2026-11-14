#pragma once
#include <cstdint>

namespace gb {

constexpr int32_t kMaxFrameBytes = 24576;

// nextInHeader is the X-Next-In value, or -1 if absent.
uint32_t nextDelayMs(bool ok, int nextInHeader, uint8_t consecutiveFailures);
bool showOffline(uint32_t msSinceLastSuccess);
bool acceptFrameLength(int32_t contentLength);

}  // namespace gb
