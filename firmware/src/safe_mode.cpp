#include "safe_mode.h"

#include <ESP8266WiFi.h>

#include "boot_guard.h"
#include "display.h"
#include "portal.h"
#include "rtc_boot.h"
#include "safe_policy.h"
#include "settings_store.h"
#include "version.h"
#include "web_ui.h"

namespace {

gb::Settings settings;
uint8_t failed = 0;
uint8_t counter = 0;
char apName[20];
bool apOn = false;

void showScreen() {
  char fail[24];
  char sta[40] = "Wi-Fi: connecting...";
  char ap[32];
  snprintf(fail, sizeof(fail), "failed boots: %u", failed);
  if (WiFi.status() == WL_CONNECTED) {
    const IPAddress ip = WiFi.localIP();
    snprintf(sta, sizeof(sta), "http://%u.%u.%u.%u/update", ip[0], ip[1], ip[2], ip[3]);
  }
  snprintf(ap, sizeof(ap), "AP %s", apName);
  const char* lines[] = {"v" GB_VERSION, fail, sta, ap, "http://192.168.4.1/update"};
  displayStatus("Safe mode", lines, apOn ? 5 : 3);
}

void handleBootNormal() {
  if (!webUiAuthorize()) return;
  rtcBootWrite(gb::markHealthy());  // next boot runs the normal firmware again
  webUiServer().send(200, F("text/plain"), F("booting normal firmware\n"));
  webUiScheduleRestart();
}

}  // namespace

void safeModeRun(uint8_t failedBoots, uint8_t bootCounter) {
  failed = failedBoots;
  counter = bootCounter;
  snprintf(apName, sizeof(apName), "GlanceBox-%04X", static_cast<unsigned>(ESP.getChipId() & 0xFFFF));

  settingsLoad(settings);
  displayBegin(settings.brightness);
  showScreen();

  if (gb::safeModeNeedsPortal(settings)) {
    // No usable update password: set one up first (same trust model as first setup).
    portalRun(settings);
  } else {
    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);
    WiFi.begin();  // saved credentials
    WiFi.setAutoReconnect(true);
  }

  StatusProvider st;
  st.safeMode = []() { return true; };
  st.bootFailed = []() { return counter; };
  webUiBeginSafe(settings, st);
  webUiServer().on("/boot-normal", HTTP_POST, handleBootNormal);

  const uint32_t wifiStart = millis();
  bool apTried = false;
  bool shownConnected = WiFi.status() == WL_CONNECTED;
  showScreen();
  for (;;) {
    webUiLoop();
    if (!apTried && gb::safeModeApFallback(WiFi.status() == WL_CONNECTED, millis() - wifiStart)) {
      // Saved network unreachable: also open an AP so /update stays reachable.
      // The station keeps reconnecting in the background.
      apTried = true;
      WiFi.mode(WIFI_AP_STA);
      apOn = WiFi.softAP(apName);
      showScreen();
    }
    const bool connected = WiFi.status() == WL_CONNECTED;
    if (connected != shownConnected) {
      shownConnected = connected;
      showScreen();
    }
    delay(1);  // yield: watchdog, Wi-Fi stack
  }
}
