#include "settings.h"

#include <cctype>
#include <cstdio>
#include <cstring>

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

template <size_t N>
void copyField(char (&dst)[N], const std::string& v) {
  std::memcpy(dst, v.data(), v.size());
  dst[v.size()] = '\0';
}

void appendJsonString(std::string& out, const char* v) {
  out += '"';
  for (const char* p = v; *p; ++p) {
    unsigned char c = static_cast<unsigned char>(*p);
    if (c == '"' || c == '\\') {
      out += '\\';
      out += static_cast<char>(c);
    } else if (c < 0x20) {
      char buf[8];
      std::snprintf(buf, sizeof(buf), "\\u%04x", c);
      out += buf;
    } else {
      out += static_cast<char>(c);
    }
  }
  out += '"';
}

// Minimal cursor-based parser for a flat JSON object of strings and integers.
class Parser {
 public:
  explicit Parser(const std::string& s) : s_(s) {}
  void ws() {
    while (i_ < s_.size() && std::isspace(static_cast<unsigned char>(s_[i_]))) ++i_;
  }
  bool eat(char c) {
    ws();
    if (i_ < s_.size() && s_[i_] == c) {
      ++i_;
      return true;
    }
    return false;
  }
  bool peek(char c) {
    ws();
    return i_ < s_.size() && s_[i_] == c;
  }
  bool atEnd() {
    ws();
    return i_ == s_.size();
  }
  bool str(std::string* out) {
    if (!eat('"')) return false;
    out->clear();
    while (i_ < s_.size()) {
      unsigned char c = static_cast<unsigned char>(s_[i_++]);
      if (c == '"') return true;
      if (c < 0x20) return false;
      if (c != '\\') {
        *out += static_cast<char>(c);
        continue;
      }
      if (i_ >= s_.size()) return false;
      char e = s_[i_++];
      switch (e) {
        case '"': *out += '"'; break;
        case '\\': *out += '\\'; break;
        case '/': *out += '/'; break;
        case 'n': *out += '\n'; break;
        case 't': *out += '\t'; break;
        case 'r': *out += '\r'; break;
        case 'u': {
          if (i_ + 4 > s_.size()) return false;
          unsigned v = 0;
          for (int k = 0; k < 4; ++k) {
            char h = s_[i_++];
            if (!std::isxdigit(static_cast<unsigned char>(h))) return false;
            v = v * 16 + static_cast<unsigned>(std::isdigit(static_cast<unsigned char>(h))
                                                   ? h - '0'
                                                   : (std::tolower(h) - 'a' + 10));
          }
          if (v == 0 || v > 0x7F) return false;  // we only ever write ASCII escapes
          *out += static_cast<char>(v);
          break;
        }
        default: return false;
      }
    }
    return false;
  }
  bool integer(long* out) {
    ws();
    bool neg = false;
    if (i_ < s_.size() && s_[i_] == '-') {
      neg = true;
      ++i_;
    }
    size_t start = i_;
    long v = 0;
    while (i_ < s_.size() && std::isdigit(static_cast<unsigned char>(s_[i_]))) {
      if (i_ - start >= 6) return false;
      v = v * 10 + (s_[i_++] - '0');
    }
    if (i_ == start) return false;
    *out = neg ? -v : v;
    return true;
  }

 private:
  const std::string& s_;
  size_t i_ = 0;
};
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

bool applyServerUrl(Settings& s, const std::string& raw, std::string* error) {
  auto url = normalizeServerUrl(raw, error);
  if (!url) return false;
  if (url->size() >= sizeof(s.serverUrl)) {
    setError(error, "too_long");
    return false;
  }
  copyField(s.serverUrl, *url);
  return true;
}

bool applyPassword(Settings& s, const std::string& pw, std::string* error) {
  if (!validPassword(pw)) {
    setError(error, "too_short");
    return false;
  }
  if (pw.size() >= sizeof(s.updatePassword)) {
    setError(error, "too_long");
    return false;
  }
  for (char c : pw) {
    // Printable ASCII only: browsers disagree on the Basic-auth charset otherwise.
    if (c < 0x20 || c > 0x7E) {
      setError(error, "invalid_chars");
      return false;
    }
  }
  copyField(s.updatePassword, pw);
  return true;
}

bool settingsComplete(const Settings& s) {
  return normalizeServerUrl(s.serverUrl, nullptr).has_value() && validPassword(s.updatePassword);
}

std::string encodeSettings(const Settings& s) {
  std::string out = "{\"server_url\":";
  appendJsonString(out, s.serverUrl);
  out += ",\"update_password\":";
  appendJsonString(out, s.updatePassword);
  out += ",\"brightness\":";
  out += std::to_string(s.brightness);
  out += "}\n";
  return out;
}

bool parseSettings(const std::string& text, Settings* out) {
  Settings r;
  Parser p(text);
  if (!p.eat('{')) return false;
  if (!p.eat('}')) {
    for (;;) {
      std::string key, sv;
      long iv = 0;
      if (!p.str(&key) || !p.eat(':')) return false;
      if (key == "server_url" || key == "update_password") {
        if (!p.str(&sv)) return false;
        if (key == "server_url") {
          if (sv.size() >= sizeof(r.serverUrl)) return false;
          copyField(r.serverUrl, sv);
        } else {
          if (sv.size() >= sizeof(r.updatePassword)) return false;
          copyField(r.updatePassword, sv);
        }
      } else if (key == "brightness") {
        if (!p.integer(&iv)) return false;
        r.brightness = clampBrightness(static_cast<int>(iv));
      } else if (p.peek('"')) {
        if (!p.str(&sv)) return false;
      } else if (!p.integer(&iv)) {
        return false;
      }
      if (p.eat(',')) continue;
      if (p.eat('}')) break;
      return false;
    }
  }
  if (!p.atEnd()) return false;
  *out = r;
  return true;
}

}  // namespace gb
