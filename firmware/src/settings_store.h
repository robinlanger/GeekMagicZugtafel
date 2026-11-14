#pragma once
#include "settings.h"

// LittleFS-backed /settings.json. Load returns false (and leaves defaults) when the
// file is missing, unreadable or corrupt; the caller then runs the portal. Load never
// writes flash; save and erase format the partition if it cannot be mounted.
bool settingsLoad(gb::Settings& s);
// Writes only when the encoded content differs from the file. Returns false on I/O error.
bool settingsSave(const gb::Settings& s);
// Deletes /settings.json (factory reset).
bool settingsErase();
