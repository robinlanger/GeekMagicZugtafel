#pragma once
#include <cstddef>
#include <cstdint>
#include <string>

namespace gb {

bool isValidMd5Hex(const std::string& s);
bool looksLikeEsp8266Image(const uint8_t* buf, size_t len);
bool fitsOta(size_t imageSize, size_t freeSketchSpace);
// Size to pass to Update.begin() when the image size is unknown (multipart upload):
// free sketch space minus one sector, rounded down to a sector (as ESP8266HTTPUpdateServer).
size_t otaBeginSize(size_t freeSketchSpace);

}  // namespace gb
