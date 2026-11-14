#include <Arduino.h>
#include <ESP8266WiFi.h>

#include "display.h"
#include "portal.h"
#include "settings_store.h"
#include "web_ui.h"

#ifndef GB_VERSION
#define GB_VERSION "dev"
#endif
static const char kVersionTag[] __attribute__((used)) = "GBVER:" GB_VERSION;

// Interim wiring (Task 12): settings, portal and web UI. Boot guard, safe mode and the
// frame loop follow in Task 13.
static gb::Settings settings;

void setup() {
  settingsLoad(settings);  // corrupt/missing file: defaults, portal asks for values
  displayBegin(settings.brightness);
  const char* starting[] = {"starting..."};
  displayStatus("Glance Box " GB_VERSION, starting, 1);

  portalRun(settings);
  webUiBegin(settings, StatusProvider{});

  const String ip = WiFi.localIP().toString();
  const char* lines[] = {ip.c_str(), settings.serverUrl};
  displayStatus("Glance Box " GB_VERSION, lines, 2);
}

void loop() { webUiLoop(); }
