#include "web_ui.h"

#include <ESP8266WiFi.h>
#include <Updater.h>
#include <WiFiUdp.h>
#include <eboot_command.h>

#include "display.h"
#include "i18n.h"
#include "ota_check.h"
#include "ota_flow.h"
#include "rtc_boot.h"
#include "settings_store.h"
#include "version.h"
#include "web_util.h"


namespace {

constexpr char kUser[] = "admin";
constexpr uint32_t kRestartDelayMs = 1000;
// Multipart framing around the image (boundaries, part headers, md5 field) is well
// below this, so contentLength - kMultipartSlack is a lower bound of the image size.
constexpr size_t kMultipartSlack = 1024;

ESP8266WebServer server(80);
gb::Settings* settings = nullptr;
StatusProvider status;
bool safeModeUi = false;
bool running = false;
bool restartPending = false;
bool wifiErasePending = false;  // factory reset: forget Wi-Fi right before restarting
uint32_t restartAtMs = 0;

// ---- OTA (one upload at a time; the server is single-threaded) ----
// Decisions live in gb::OtaFlow (native-tested); this file only executes them.
gb::OtaFlow flow;
char otaMd5[33];

Lang requestLang() { return langFromHeader(server.header(F("Accept-Language"))); }

bool originOk() {
  return gb::originAllowed(server.header(F("Origin")).c_str(), server.hostHeader().c_str());
}

bool credentialsOk() {
  // Never accept an unset/short password.
  return settings != nullptr && gb::validPassword(settings->updatePassword) &&
         server.authenticate(kUser, settings->updatePassword);
}

// Drop an uncommitted update: abort the Updater and clear any eboot copy command, so
// the running image stays the one that boots. Never called once an image is committed.
void otaDiscard() {
  if (!flow.mayDiscard()) return;
  if (Update.isRunning()) {
    // end(false) only aborts while bytes are missing; if the image happens to be complete,
    // a bogus MD5 makes end() fail instead of staging it.
    if (Update.isFinished() && !Update.hasError()) Update.setMD5("00000000000000000000000000000000");
    Update.end(false);
    if (Update.isRunning()) Update.end(false);  // end() keeps state after an MD5 mismatch
  }
  eboot_command_clear();
}

// After every upload event: on failure discard (unless committed) and tell the screen.
void otaSettle(gb::OtaError before) {
  if (!flow.failed()) return;
  otaDiscard();
  // Unauthenticated requests must not touch the display; after a commit the screen keeps
  // "Update OK" because the staged image boots next regardless.
  if (before == gb::OtaError::None && flow.authorized() && !flow.committed()) {
    const char* lines[] = {gb::otaErrorText(flow.error())};
    displayStatus("Update failed", lines, 1);
  }
}

gb::OtaError otaEndError(uint8_t updaterError) {
  if (updaterError == UPDATE_ERROR_MD5) return gb::OtaError::Md5Mismatch;
  if (updaterError == UPDATE_ERROR_MAGIC_BYTE || updaterError == UPDATE_ERROR_NEW_FLASH_CONFIG)
    return gb::OtaError::Header;
  return gb::OtaError::Verify;
}

void handleUpload() {
  HTTPUpload& up = server.upload();
  const gb::OtaError before = flow.error();
  switch (up.status) {
    case UPLOAD_FILE_START: {
      const bool origin = originOk();
      const bool auth = origin && credentialsOk();
      const String md5 = server.arg(F("md5"));
      const size_t minImage =
          up.contentLength > kMultipartSlack ? up.contentLength - kMultipartSlack : 0;
      const size_t beginSize = gb::otaBeginSize(ESP.getFreeSketchSpace());
      flow.onFileStart({origin, auth, up.name == F("firmware"), gb::isValidMd5Hex(md5.c_str()),
                        beginSize > 0 && gb::fitsOta(minImage, beginSize)});
      if (!flow.failed()) {
        strlcpy(otaMd5, md5.c_str(), sizeof(otaMd5));
        const char* lines[] = {"receiving..."};
        displayStatus("Firmware update", lines, 1);
      }
      break;
    }
    case UPLOAD_FILE_WRITE: {
      const auto step = flow.onChunk(gb::looksLikeEsp8266Image(up.buf, up.currentSize));
      if (step == gb::OtaFlow::Chunk::Skip) break;
      if (step == gb::OtaFlow::Chunk::BeginAndWrite) {
        WiFiUDP::stopAll();
        eboot_command_clear();  // no stale copy command may survive into this update
        flow.onBegin(Update.begin(gb::otaBeginSize(ESP.getFreeSketchSpace())) &&
                     Update.setMD5(otaMd5));
        if (flow.failed()) break;
      }
      const bool ok = Update.write(up.buf, up.currentSize) == up.currentSize;
      flow.onWrite(ok, !ok && Update.getError() == UPDATE_ERROR_SPACE);
      break;
    }
    case UPLOAD_FILE_END: {
      if (flow.onFileEnd() == gb::OtaFlow::End::Skip) break;
      const bool ok = Update.end(true);  // verifies size, MD5, header; stages eboot copy
      if (flow.onFinished(ok, ok ? gb::OtaError::None : otaEndError(Update.getError()))) {
        // Commit point: whatever happens to this request now, the staged image boots
        // next, with a clean boot counter.
        rtcBootWrite(gb::markHealthy());
        const char* lines[] = {"restarting..."};
        displayStatus("Update OK", lines, 1);
        webUiScheduleRestart();
      }
      break;
    }
    case UPLOAD_FILE_ABORTED:
    default:
      flow.onAborted();
      break;
  }
  otaSettle(before);
}

void handleUpdateDone() {
  if (!flow.started()) {
    // No file part at all: still enforce origin/auth before saying anything.
    if (!originOk()) return server.send(403, F("text/plain"), F("origin not allowed\n"));
    if (!credentialsOk()) return server.requestAuthentication();
    return server.send(400, F("text/plain"), F("update failed: firmware missing\n"));
  }
  const gb::OtaResponse r = flow.response();
  if (r.code == 401) return server.requestAuthentication();
  if (r.code == 200) return server.send(200, F("text/plain"), F("update ok, restarting\n"));
  String msg = F("update failed: ");
  msg += gb::otaErrorText(r.error);
  msg += '\n';
  server.send(r.code, F("text/plain"), msg);
}

uint32_t uptimeS() { return static_cast<uint32_t>(micros64() / 1000000ULL); }

String statusJson() {
  const bool wifi = WiFi.status() == WL_CONNECTED;
  const int32_t age = status.lastFrameAgeS ? status.lastFrameAgeS() : -1;
  char rssi[8] = "null";
  if (wifi) snprintf(rssi, sizeof(rssi), "%d", WiFi.RSSI());
  char ageBuf[12] = "null";
  if (age >= 0) snprintf(ageBuf, sizeof(ageBuf), "%ld", static_cast<long>(age));
  const String reset = ESP.getResetReason();
  char buf[384];
  snprintf_P(buf, sizeof(buf),
             PSTR("{\"version\":\"%s\",\"uptime_s\":%lu,\"heap_free\":%u,\"rssi\":%s,"
                  "\"boot_failed\":%u,\"safe_mode\":%s,\"frames_ok\":%lu,"
                  "\"last_frame_age_s\":%s,\"flash_size\":%u,\"reset_reason\":\"%s\"}"),
             gbVersion(), static_cast<unsigned long>(uptimeS()),
             static_cast<unsigned>(ESP.getFreeHeap()), rssi,
             static_cast<unsigned>(status.bootFailed ? status.bootFailed() : 0),
             (status.safeMode ? status.safeMode() : safeModeUi) ? "true" : "false",
             static_cast<unsigned long>(status.framesOk ? status.framesOk() : 0), ageBuf,
             static_cast<unsigned>(ESP.getFlashChipRealSize()), reset.c_str());
  return String(buf);
}

void handleStatus() {
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.send(200, F("application/json"), statusJson());
}

void handleRestart() {
  if (!webUiAuthorize()) return;
  server.send(200, F("text/plain"), String(tr(requestLang(), Msg::Restarting)) + '\n');
  webUiScheduleRestart();
}

// ---- HTML pages (normal mode only) ----

const char kHead[] PROGMEM =
    "<!doctype html><meta charset=utf-8><meta name=viewport "
    "content='width=device-width,initial-scale=1'><title>Glance Box</title><style>"
    "body{font-family:sans-serif;max-width:34em;margin:1em auto;padding:0 1em}"
    "input{display:block;width:100%;box-sizing:border-box;margin:.2em 0 .8em}"
    "td{padding:.1em 1em .1em 0}button{padding:.4em 1em;margin:.2em 0}"
    ".ok{color:#070}.err{color:#b00}</style><h1>Glance Box</h1>";

void addRow(String& p, const __FlashStringHelper* label, const String& value) {
  p += F("<tr><td>");
  p += label;
  p += F("<td>");
  p += value;
}

void sendPage(int code, const String& body) {
  String p;
  p.reserve(body.length() + sizeof(kHead));
  p += FPSTR(kHead);
  p += body;
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.send(code, F("text/html; charset=utf-8"), p);
}

void sendMessage(int code, Lang lang, const __FlashStringHelper* msg, bool error) {
  String b = error ? F("<p class=err>") : F("<p class=ok>");
  b += msg;
  b += F("<p><a href='/'>");
  b += tr(lang, Msg::Back);
  b += F("</a>");
  sendPage(code, b);
}

void handleRoot() {
  const Lang l = requestLang();
  const bool wifi = WiFi.status() == WL_CONNECTED;
  const int32_t age = status.lastFrameAgeS ? status.lastFrameAgeS() : -1;
  String b;
  b.reserve(2600);
  if (server.hasArg(F("saved"))) {
    b += F("<p class=ok>");
    b += tr(l, Msg::Saved);
    b += F("</p>");
  }
  b += F("<h2>");
  b += tr(l, Msg::Status);
  b += F("</h2><table>");
  addRow(b, F("Version"), F(GB_VERSION));
  addRow(b, F("IP"), WiFi.localIP().toString());
  addRow(b, tr(l, Msg::Uptime), String(uptimeS()) + F(" s"));
  addRow(b, tr(l, Msg::Signal), wifi ? String(WiFi.RSSI()) + F(" dBm") : String('-'));
  addRow(b, tr(l, Msg::Frames), String(status.framesOk ? status.framesOk() : 0));
  addRow(b, tr(l, Msg::LastFrame), age >= 0 ? String(age) + F(" s") : String('-'));
  addRow(b, tr(l, Msg::BootFailures), String(status.bootFailed ? status.bootFailed() : 0));
  addRow(b, tr(l, Msg::SafeMode),
         (status.safeMode ? status.safeMode() : safeModeUi) ? F("on") : F("off"));
  b += F("</table><h2>");
  b += tr(l, Msg::Settings);
  b += F("</h2><p><small>");
  b += tr(l, Msg::AuthHint);
  b += F("</small><form method=post action=/settings><label>");
  b += tr(l, Msg::ServerUrl);
  b += F("<input name=server_url maxlength=95 required value='");
  b += gb::htmlEscape(settings->serverUrl).c_str();
  b += F("'></label><label>");
  b += tr(l, Msg::Brightness);
  b += F("<input name=brightness type=number min=5 max=100 required value=");
  b += settings->brightness;
  b += F("></label><label>");
  b += tr(l, Msg::NewPassword);
  b += F("<input name=password type=password maxlength=32 autocomplete=new-password>"
         "</label><button>");
  b += tr(l, Msg::Save);
  b += F("</button></form><h2>");
  b += tr(l, Msg::FirmwareUpdate);
  // md5 must precede the file input: fields are sent in document order.
  b += F("</h2><form method=post action=/update enctype=multipart/form-data><label>");
  b += tr(l, Msg::Md5Label);
  b += F("<input name=md5 required pattern='[0-9a-fA-F]{32}'></label>"
         "<input type=file name=firmware accept='.bin' required><button>");
  b += tr(l, Msg::Upload);
  b += F("</button></form><h2>");
  b += tr(l, Msg::Device);
  b += F("</h2><form method=post action=/restart><button>");
  b += tr(l, Msg::Restart);
  b += F("</button></form><form method=post action=/reset onsubmit=\"return confirm('");
  b += tr(l, Msg::ResetConfirm);
  b += F("')\"><button>");
  b += tr(l, Msg::Reset);
  b += F("</button></form>");
  sendPage(200, b);
}

void handleSettings() {
  if (!webUiAuthorize()) return;
  const Lang l = requestLang();
  gb::Settings next = *settings;
  std::string err;
  if (!gb::applyServerUrl(next, server.arg(F("server_url")).c_str(), &err)) {
    return sendMessage(400, l, tr(l, msgForError(err, false)), true);
  }
  const String pw = server.arg(F("password"));
  if (pw.length() > 0 && !gb::applyPassword(next, pw.c_str(), &err)) {
    return sendMessage(400, l, tr(l, msgForError(err, true)), true);
  }
  const String br = server.arg(F("brightness"));
  char* end = nullptr;
  const long pct = strtol(br.c_str(), &end, 10);
  if (br.length() == 0 || *end != '\0' || pct < 5 || pct > 100) {
    return sendMessage(400, l, tr(l, Msg::ErrBrightness), true);
  }
  next.brightness = gb::clampBrightness(static_cast<int>(pct));
  if (!settingsSave(next)) return sendMessage(500, l, tr(l, Msg::ErrSaveFailed), true);
  *settings = next;
  displaySetBrightness(settings->brightness);
  server.sendHeader(F("Location"), F("/?saved=1"));
  server.send(303);
}

void handleReset() {
  if (!webUiAuthorize()) return;
  const Lang l = requestLang();
  if (!settingsErase()) {  // keep running unchanged: no half reset
    return sendMessage(500, l, tr(l, Msg::ErrResetFailed), true);
  }
  sendMessage(200, l, tr(l, Msg::ResetDone), false);  // before Wi-Fi goes away
  wifiErasePending = true;
  webUiScheduleRestart();
}

void beginCommon(gb::Settings& s, const StatusProvider& st, bool safe) {
  settings = &s;
  status = st;
  safeModeUi = safe;
  server.collectHeaders("Accept-Language", "Origin");
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/update", HTTP_POST, handleUpdateDone, handleUpload);
  server.on("/restart", HTTP_POST, handleRestart);
}

void start() {
  server.onNotFound([]() { server.send(404, F("text/plain"), F("not found\n")); });
  server.begin();
  running = true;
}

}  // namespace

void webUiBegin(gb::Settings& s, const StatusProvider& st) {
  beginCommon(s, st, false);
  server.on("/", HTTP_GET, handleRoot);
  server.on("/settings", HTTP_POST, handleSettings);
  server.on("/reset", HTTP_POST, handleReset);
  start();
}

void webUiBeginSafe(gb::Settings& s, const StatusProvider& st) {
  beginCommon(s, st, true);
  start();
}

void webUiLoop() {
  server.handleClient();
  // Uploads are parsed synchronously inside handleClient(), so upload state left here
  // belongs to a broken request (parse error, client gone): drop it.
  if (Update.isRunning()) otaDiscard();  // never true after a commit (Update is reset then)
  flow.endRequest();
  if (restartPending && static_cast<int32_t>(millis() - restartAtMs) >= 0) {
    server.stop();
    if (wifiErasePending) {
      WiFi.persistent(true);
      WiFi.disconnect(true);  // forget stored Wi-Fi credentials
      ESP.eraseConfig();
    }
    ESP.restart();
  }
}

ESP8266WebServer& webUiServer() { return server; }

bool webUiAuthorize() {
  if (!originOk()) {
    server.send(403, F("text/plain"), F("origin not allowed\n"));
    return false;
  }
  if (!credentialsOk()) {
    server.requestAuthentication();
    return false;
  }
  return true;
}

void webUiScheduleRestart() {
  restartPending = true;
  restartAtMs = millis() + kRestartDelayMs;
}

bool webUiRunning() { return running; }
