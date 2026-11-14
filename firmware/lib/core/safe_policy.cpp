#include "safe_policy.h"

namespace gb {

bool safeModeNeedsPortal(const Settings& s) { return !validPassword(s.updatePassword); }

bool safeModeApFallback(bool staConnected, uint32_t msSinceWifiStart) {
  return !staConnected && msSinceWifiStart >= kSafeModeConnectMs;
}

}  // namespace gb
