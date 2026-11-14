#pragma once
#include <cstddef>
#include <cstdint>

namespace gb {

// Fixed ETag buffer (char[40]) on the device: longer tags are not stored.
constexpr size_t kEtagCap = 40;
constexpr size_t kErrorTextCap = 32;

// Frame fetch status codes: HTTP status (> 0), HTTPClient errors (-1..-11) or these.
constexpr int kErrFrameLength = -100;  // Content-Length missing, 0 or > kMaxFrameBytes
constexpr int kErrBodyRead = -101;     // body shorter than Content-Length before the deadline
constexpr int kErrDecode = -102;       // JPEG could not be decoded
constexpr int kErrNoWifi = -103;       // no request made: Wi-Fi not connected
constexpr int kErrBadUrl = -104;       // request URL could not be built/parsed

// X-Next-In header value in whole seconds; -1 when absent or malformed.
// Large values saturate (nextDelayMs clamps them to 30 s).
int parseNextIn(const char* header);
// Copies src into dst if it fits including the terminator; otherwise dst becomes "".
bool storeEtag(char (&dst)[kEtagCap], const char* src);
// Short ASCII text for the offline screen, always NUL-terminated (truncated to cap).
void frameErrorText(int status, char* buf, size_t cap);

struct PollOutcome {
  uint32_t delayMs;  // until the next request
  bool drawOffline;  // (re)draw the offline status screen now
  bool clearEtag;    // the display no longer shows the frame of the stored ETag
};

// Poll loop state: backoff, offline screen after 120 s without success (once per
// outage, redrawn only when the error changes). Times are millis() values; wraparound safe.
class FramePoller {
 public:
  void begin(uint32_t nowMs);
  // 200 (displayed) or 304. nextIn: parsed X-Next-In or -1.
  PollOutcome onSuccess(int nextIn, uint32_t nowMs);
  PollOutcome onFailure(int status, uint32_t nowMs);
  bool offline() const { return offline_; }
  uint8_t failures() const { return failures_; }

 private:
  uint32_t lastSuccessMs_ = 0;
  uint8_t failures_ = 0;
  bool offline_ = false;
  int offlineStatus_ = 0;
};

}  // namespace gb
