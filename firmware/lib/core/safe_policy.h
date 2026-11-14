#pragma once
#include <cstdint>

#include "settings.h"

namespace gb {

// Safe mode waits this long for the saved Wi-Fi before it also opens its own AP.
constexpr uint32_t kSafeModeConnectMs = 20000;

// Safe mode can only accept an update with a valid update password. Without one
// (settings missing or corrupt) it runs the setup portal first, with the same trust
// model as the first setup. The server URL does not matter in safe mode.
bool safeModeNeedsPortal(const Settings& s);
// True once the saved network has not connected within kSafeModeConnectMs.
bool safeModeApFallback(bool staConnected, uint32_t msSinceWifiStart);

}  // namespace gb
