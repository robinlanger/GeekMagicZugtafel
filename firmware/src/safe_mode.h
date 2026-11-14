#pragma once
#include <cstdint>

// Boot-loop safe mode (spec 5.4): Wi-Fi (saved credentials, AP fallback), web UI with
// only /status, /update, /restart and POST /boot-normal, and a status screen.
// No frame client, no JPEG decoding. Never returns.
// failedBoots: failures that led here; bootCounter: value now stored in RTC memory.
[[noreturn]] void safeModeRun(uint8_t failedBoots, uint8_t bootCounter);
