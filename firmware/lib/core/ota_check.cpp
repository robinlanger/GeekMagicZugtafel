#include "ota_check.h"

#include <cctype>

namespace gb {

bool isValidMd5Hex(const std::string& s) {
  if (s.size() != 32) return false;
  for (char c : s) {
    if (!std::isxdigit(static_cast<unsigned char>(c))) return false;
  }
  return true;
}

bool looksLikeEsp8266Image(const uint8_t* buf, size_t len) {
  return buf != nullptr && len >= 4 && buf[0] == 0xE9;
}

bool fitsOta(size_t imageSize, size_t freeSketchSpace) {
  return imageSize <= freeSketchSpace;
}

size_t otaBeginSize(size_t freeSketchSpace) {
  constexpr size_t kSector = 0x1000;
  if (freeSketchSpace <= kSector) return 0;
  return (freeSketchSpace - kSector) & ~(kSector - 1);
}

}  // namespace gb
