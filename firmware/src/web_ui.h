#pragma once
// Device web UI on port 80: status page, settings, restart/reset, /status JSON and
// the verified OTA endpoint POST /update.
//
// OTA clients: send the md5 field BEFORE the file part, e.g.
//   curl -u admin:<pw> -F md5=<hex> -F firmware=@firmware.bin http://<ip>/update
// (md5 may also be given as query parameter: /update?md5=<hex>).
#include <ESP8266WebServer.h>

#include "settings.h"

// Dynamic status fields owned by the main loop. Any pointer may be null (field then
// reports 0 / false / null).
struct StatusProvider {
  uint32_t (*framesOk)() = nullptr;
  int32_t (*lastFrameAgeS)() = nullptr;  // < 0: no frame yet (reported as null)
  bool (*safeMode)() = nullptr;
  uint8_t (*bootFailed)() = nullptr;
};

// Normal mode: GET /, GET /update (redirect to the form), POST /settings, /restart, /reset, GET /status, POST /update.
void webUiBegin(gb::Settings& settings, const StatusProvider& status);
// Safe mode: GET / and /update (minimal page with the update form), GET /status,
// POST /update, POST /restart (same OTA code path).
// Further routes (e.g. /boot-normal) can be added via webUiServer() before or after.
void webUiBeginSafe(gb::Settings& settings, const StatusProvider& status);
void webUiLoop();

// Hooks for additional routes. Never call collectHeaders() on it: that replaces the
// header list of web_ui.cpp (kCollectedHeaders), and the Origin check then refuses
// every state-changing request.
ESP8266WebServer& webUiServer();
// Origin (CSRF) check plus Basic auth "admin"/update password. Sends 403/401 itself
// and returns false when the request must not proceed.
bool webUiAuthorize();
// Restart about 1 s from now (lets the response reach the client).
void webUiScheduleRestart();
bool webUiRunning();
