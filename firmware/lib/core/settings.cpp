#include "settings.h"

#include <cctype>

namespace gb {

namespace {
bool ieq(const std::string& s, size_t pos, const char* lit) {
  for (size_t i = 0; lit[i]; ++i) {
    if (pos + i >= s.size() ||
        std::tolower(static_cast<unsigned char>(s[pos + i])) != lit[i])
      return false;
  }
  return true;
}
void setError(std::string* e, const char* v) {
  if (e) *e = v;
}
}  // namespace

std::optional<std::string> normalizeServerUrl(std::string in, std::string* error) {
  size_t b = 0, e = in.size();
  while (b < e && std::isspace(static_cast<unsigned char>(in[b]))) ++b;
  while (e > b && std::isspace(static_cast<unsigned char>(in[e - 1]))) --e;
  std::string s = in.substr(b, e - b);

  if (ieq(s, 0, "https://")) {
    setError(error, "https_unsupported");
    return std::nullopt;
  }
  if (ieq(s, 0, "http://")) {
    s = "http://" + s.substr(7);
  } else if (s.find("://") == std::string::npos) {
    s = "http://" + s;
  } else {
    setError(error, "unsupported_scheme");
    return std::nullopt;
  }
  while (s.size() > 7 && s.back() == '/') s.pop_back();

  std::string rest = s.substr(7);
  size_t slash = rest.find('/');
  std::string hostport = rest.substr(0, slash);
  size_t colon = hostport.find(':');
  std::string host = hostport.substr(0, colon);
  if (host.empty()) {
    setError(error, "empty_host");
    return std::nullopt;
  }
  return s;
}

bool validPassword(const std::string& pw) { return pw.size() >= 8; }

uint8_t clampBrightness(int pct) {
  if (pct < 5) return 5;
  if (pct > 100) return 100;
  return static_cast<uint8_t>(pct);
}

}  // namespace gb
