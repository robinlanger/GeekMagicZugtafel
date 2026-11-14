#pragma once
#include "settings.h"

// Captive portal (AP "GlanceBox-XXXX") for Wi-Fi, server URL, update password and
// brightness. Values are validated with the gb:: core functions and saved to
// /settings.json. Blocks until Wi-Fi is connected and settings are complete.
// Exception: an already configured device whose Wi-Fi is unreachable gets the portal
// for a limited time only, then returns and keeps reconnecting in the background.
void portalRun(gb::Settings& settings);
