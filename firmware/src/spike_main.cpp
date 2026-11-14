// Hardware spike (never shipped): verifies pins, colours, orientation and flash size.
#include <Arduino.h>
#include <ESP8266HTTPUpdateServer.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>

#include "display.h"
#include "version.h"


static ESP8266WebServer server(80);
static ESP8266HTTPUpdateServer updater;

static String statusJson() {
  String j = "{";
  j += "\"version\":\"";
  j += gbVersion();
  j += '"';
  j += ",\"flash_real_size\":" + String(ESP.getFlashChipRealSize());
  j += ",\"flash_ide_size\":" + String(ESP.getFlashChipSize());
  j += ",\"sketch_size\":" + String(ESP.getSketchSize());
  j += ",\"free_sketch_space\":" + String(ESP.getFreeSketchSpace());
  j += ",\"heap_free\":" + String(ESP.getFreeHeap());
  j += ",\"chip_id\":\"" + String(ESP.getChipId(), HEX) + "\"";
  j += ",\"reset_reason\":\"" + ESP.getResetReason() + "\"";
  j += "}";
  return j;
}

// R/G/B bars, white border (offset check), orientation markers. No umlauts: built-in fonts lack them.
static void drawTestPattern() {
  TFT_eSPI& t = displayTft();
  t.fillScreen(TFT_BLACK);
  t.fillRect(0, 60, 80, 120, TFT_RED);
  t.fillRect(80, 60, 80, 120, TFT_GREEN);
  t.fillRect(160, 60, 80, 120, TFT_BLUE);
  t.drawRect(0, 0, 240, 240, TFT_WHITE);
  t.drawRect(1, 1, 238, 238, TFT_WHITE);
  t.setTextColor(TFT_WHITE, TFT_BLACK);
  t.setTextDatum(TL_DATUM);
  t.drawString("TOP", 8, 8, 4);
  t.fillTriangle(210, 8, 200, 28, 220, 28, TFT_YELLOW);  // arrow pointing up, top-right
  t.setTextColor(TFT_BLACK, TFT_RED);
  t.drawString("R", 36, 110, 4);
  t.setTextColor(TFT_BLACK, TFT_GREEN);
  t.drawString("G", 116, 110, 4);
  t.setTextColor(TFT_WHITE, TFT_BLUE);
  t.drawString("B", 196, 110, 4);
}

static void showInfo() {
  TFT_eSPI& t = displayTft();
  t.setTextColor(TFT_WHITE, TFT_BLACK);
  t.setTextDatum(TL_DATUM);
  String l[5] = {
      "v" GB_VERSION " " + WiFi.localIP().toString(),
      "flash real " + String(ESP.getFlashChipRealSize()),
      "flash ide  " + String(ESP.getFlashChipSize()),
      "sketch free " + String(ESP.getFreeSketchSpace()),
      "heap " + String(ESP.getFreeHeap()),
  };
  for (int i = 0; i < 5; i++) t.drawString(l[i], 6, 186 + i * 10, 1);
}

void setup() {
  Serial.begin(115200);
  displayBegin(80);
  drawTestPattern();

  char ap[24];
  snprintf(ap, sizeof(ap), "GlanceBox-%04X", (unsigned)(ESP.getChipId() & 0xFFFF));
  WiFiManager wm;
  wm.autoConnect(ap);

  server.on("/status", HTTP_GET, []() { server.send(200, "application/json", statusJson()); });
  updater.setup(&server, "/update");  // no password: spike only
  server.begin();
  showInfo();
  Serial.println(statusJson());
}

void loop() { server.handleClient(); }
