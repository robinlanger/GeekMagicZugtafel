#include "settings_store.h"

#include <LittleFS.h>

namespace {
constexpr char kPath[] = "/settings.json";
constexpr char kTmpPath[] = "/settings.tmp";
constexpr size_t kMaxFileBytes = 512;

bool mounted = false;

// Never auto-format: a failed mount at boot (stock firmware's data, a future layout
// change) must not erase the partition and with it the update password. Only the
// user-initiated writes (save, factory reset) may format, see mountForWrite().
bool mount() {
  if (mounted) return true;
  LittleFSConfig cfg;
  cfg.setAutoFormat(false);
  LittleFS.setConfig(cfg);  // only fails while mounted, which we are not
  mounted = LittleFS.begin();
  return mounted;
}

bool mountForWrite() {
  if (mount()) return true;
  // Unusable file system: the user asked us to write, so start a fresh one.
  mounted = LittleFS.format() && LittleFS.begin();
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

// Read-only: never writes flash (a mount failure just leaves the defaults).
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
  if (!mountForWrite()) return false;
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
  if (!mountForWrite()) return false;
  LittleFS.remove(kTmpPath);
  return !LittleFS.exists(kPath) || LittleFS.remove(kPath);
}
