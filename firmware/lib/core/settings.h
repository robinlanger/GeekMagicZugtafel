#pragma once
#include <cstdint>
#include <optional>
#include <string>

namespace gb {

// Returns the normalized "http://host[:port][/path]" URL without trailing
// slash, or nullopt with *error set ("https_unsupported", "empty_host").
std::optional<std::string> normalizeServerUrl(std::string in, std::string* error);
bool validPassword(const std::string& pw);
uint8_t clampBrightness(int pct);

}  // namespace gb
