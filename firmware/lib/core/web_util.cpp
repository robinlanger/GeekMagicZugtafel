#include "web_util.h"

#include <cctype>

namespace gb {

bool prefersGerman(const char* al) {
  if (al == nullptr) return false;
  while (*al == ' ') ++al;
  if (std::tolower(static_cast<unsigned char>(al[0])) != 'd' ||
      std::tolower(static_cast<unsigned char>(al[1])) != 'e')
    return false;
  return !std::isalpha(static_cast<unsigned char>(al[2]));
}

std::string htmlEscape(const std::string& in) {
  std::string out;
  out.reserve(in.size());
  for (char c : in) {
    switch (c) {
      case '&': out += "&amp;"; break;
      case '<': out += "&lt;"; break;
      case '>': out += "&gt;"; break;
      case '"': out += "&quot;"; break;
      case '\'': out += "&#39;"; break;
      default: out += c;
    }
  }
  return out;
}

bool originAllowed(const std::string& origin, const std::string& host) {
  if (origin.empty()) return true;
  if (host.empty()) return false;
  const std::string expected = "http://" + host;
  if (origin.size() != expected.size()) return false;
  for (size_t i = 0; i < origin.size(); ++i) {
    if (std::tolower(static_cast<unsigned char>(origin[i])) !=
        std::tolower(static_cast<unsigned char>(expected[i])))
      return false;
  }
  return true;
}

}  // namespace gb
