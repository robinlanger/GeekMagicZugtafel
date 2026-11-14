#include "settings_store.h"

#include <LittleFS.h>

namespace {
constexpr char kPath[] = "/settings.json";
constexpr char kTmpPath[] = "/settings.tmp";
constexpr size_t kMaxFileBytes = 512;

bool mounted = false;

bool mount() {
  if (!mounted) mounted = LittleFS.begin();
  return mounted;
}

bool readFile(std::string* out) {
  File f = LittleFS.open(kPath, "r");
  if (!f) return false;
  size_t n = f.size();
  if (n > kMaxFileBytes) {
    f.close();
    return false;
  }
  out->resize(n);
  size_t got = f.read(reinterpret_cast<uint8_t*>(&(*out)[0]), n);
  f.close();
  return got == n;
}
}  // namespace

bool settingsLoad(gb::Settings& s) {
  s = gb::Settings();
  std::string text;
  if (!mount() || !readFile(&text)) return false;
  gb::Settings parsed;
  if (!gb::parseSettings(text, &parsed)) return false;
  s = parsed;
  return true;
}

bool settingsSave(const gb::Settings& s) {
  if (!mount()) return false;
  const std::string text = gb::encodeSettings(s);
  std::string current;
  if (readFile(&current) && current == text) return true;  // unchanged: no flash write
  // Write to a temp file and rename, so a power cut never leaves a half-written file.
  File f = LittleFS.open(kTmpPath, "w");
  if (!f) return false;
  size_t written = f.write(reinterpret_cast<const uint8_t*>(text.data()), text.size());
  f.close();
  if (written != text.size()) {
    LittleFS.remove(kTmpPath);
    return false;
  }
  return LittleFS.rename(kTmpPath, kPath);  // lfs_rename replaces the target atomically
}

bool settingsErase() {
  if (!mount()) return false;
  LittleFS.remove(kTmpPath);
  return !LittleFS.exists(kPath) || LittleFS.remove(kPath);
}
