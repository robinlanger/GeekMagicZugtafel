#pragma once
#include <cstddef>
#include <cstdint>

namespace gb {

// Must equal MAX_JPEG_BYTES in server/glancebox/render.py (checked by
// server/tests/test_frame_limit_parity.py).
constexpr int32_t kMaxFrameBytes = 24576;
// Static TJpgDec work pool (src/display.cpp). Measured need (test_tjpgd fixtures):
// server-style (optimized tables) 2652 B, standard tables 4:4:4 2776 B, 4:2:0 3480 B.
// 4096 leaves room for encoders with larger custom tables.
constexpr size_t kJpegPoolBytes = 4096;

// nextInHeader is the X-Next-In value, or -1 if absent.
uint32_t nextDelayMs(bool ok, int nextInHeader, uint8_t consecutiveFailures);
bool showOffline(uint32_t msSinceLastSuccess);
bool acceptFrameLength(int32_t contentLength);

}  // namespace gb
