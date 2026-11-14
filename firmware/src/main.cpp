#include <Arduino.h>
#include <ESP8266WiFi.h>

#include "boot_guard.h"
#include "display.h"
#include "frame_client.h"
#include "frame_poll.h"
#include "portal.h"
#include "rtc_boot.h"
#include "safe_mode.h"
#include "settings_store.h"
#include "version.h"
#include "web_ui.h"

static_assert(gb::kResetReasonPowerOn == REASON_DEFAULT_RST, "rst_reason changed");
static_assert(gb::kResetReasonExtPin == REASON_EXT_SYS_RST, "rst_reason changed");

namespace {

gb::Settings settings;
gb::BootState bootState{0, 0};  // as stored in RTC memory
gb::HealthLatch health;
gb::FramePoller poller;

char etag[gb::kEtagCap] = "";
char lastError[gb::kErrorTextCap] = "";
uint32_t framesOk = 0;
uint32_t lastSuccessMs = 0;
bool anySuccess = false;
uint32_t nextPollMs = 0;

void formatIp(char* buf, size_t cap) {
  const IPAddress ip = WiFi.localIP();
  snprintf(buf, cap, "%u.%u.%u.%u", ip[0], ip[1], ip[2], ip[3]);
}

void showBootScreen() {
  char ip[20];
  formatIp(ip, sizeof(ip));
  const char* lines[] = {ip, settings.serverUrl, "waiting for first frame..."};
  displayStatus("Glance Box " GB_VERSION, lines, 3);
}

void showOfflineScreen() {
  char ip[20];
  formatIp(ip, sizeof(ip));
  const char* lines[] = {"Server not reachable", ip, settings.serverUrl, lastError};
  displayStatus("Glance Box offline", lines, 4);
}

// One request/response cycle. No String building here: buffers are fixed-size.
void pollFrame() {
  int status = gb::kErrNoWifi;
  int nextIn = -1;
  if (WiFi.status() == WL_CONNECTED) {
    const FrameResult r = fetchFrame(settings.serverUrl, etag);
    status = r.status;
    nextIn = r.nextIn;
    if (status == 200) {  // already drawn (stream decode)
      memcpy(etag, r.etag, sizeof(etag));
      ++framesOk;
    }
  }
  const uint32_t now = millis();  // after the request, which may take seconds
  gb::PollOutcome o;
  if (status == 200 || status == 304) {
    o = poller.onSuccess(nextIn, now);
    lastSuccessMs = now;
    anySuccess = true;
  } else {
    gb::frameErrorText(status, lastError, sizeof(lastError));
    Serial.printf("frame poll failed: %s (%d)\n", lastError, status);
    o = poller.onFailure(status, now);
  }
  if (o.clearEtag) etag[0] = '\0';
  if (o.drawOffline) showOfflineScreen();
  nextPollMs = now + o.delayMs;
}

}  // namespace

void setup() {
  // 1. Boot guard first: before display, Wi-Fi or anything else that could crash.
  const gb::BootState stored = rtcBootRead();
  const gb::ResetKind kind = gb::resetKindFromReason(ESP.getResetInfoPtr()->reason);
  const gb::BootDecision boot = gb::onBoot(stored, kind);
  rtcBootWrite(boot.next);
  bootState = boot.next;

  // 2. Too many failed boots: minimal safe mode (never returns).
  if (boot.safeMode) safeModeRun(stored.failed, boot.next.failed);

  // 3. Normal firmware.
  Serial.begin(115200);
  displayBegin(gb::kDefaultBrightness);
  const char* starting[] = {"starting..."};
  displayStatus("Glance Box " GB_VERSION, starting, 1);
  settingsLoad(settings);  // corrupt/missing file: defaults, portal asks for values
  displaySetBrightness(settings.brightness);

  portalRun(settings);
  StatusProvider st;
  st.framesOk = []() { return framesOk; };
  st.lastFrameAgeS = []() -> int32_t {
    return anySuccess ? static_cast<int32_t>((millis() - lastSuccessMs) / 1000) : -1;
  };
  st.safeMode = []() { return false; };
  st.bootFailed = []() { return bootState.failed; };
  webUiBegin(settings, st);

  showBootScreen();
  poller.begin(millis());
  nextPollMs = millis();
}

void loop() {
  webUiLoop();

  const uint32_t now = millis();
  if (health.shouldMark(now, WiFi.status() == WL_CONNECTED, webUiRunning())) {
    bootState = gb::markHealthy();
    rtcBootWrite(bootState);  // once per boot
  }

#ifdef GB_CRASH_TEST
  // Test build only: crash 5 s after boot to exercise the boot-loop guard.
  if (now >= 5000) abort();
#endif

  if (static_cast<int32_t>(now - nextPollMs) >= 0) pollFrame();
  delay(1);  // yield: watchdog, Wi-Fi stack
}
