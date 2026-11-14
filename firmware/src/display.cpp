#include "display.h"

#include <TJpg_Decoder.h>

#include "settings.h"

namespace {
constexpr uint8_t kBacklightPin = 5;
constexpr int kPwmRange = 100;
constexpr int kHeight = 240;

TFT_eSPI tft;

bool tftOutput(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap) {
  if (y >= kHeight) return false;
  tft.pushImage(x, y, w, h, bitmap);
  return true;
}
}  // namespace

TFT_eSPI& displayTft() { return tft; }

void displaySetBrightness(uint8_t pct) {
  // Backlight is active-low: duty = max - scaled percentage.
  analogWrite(kBacklightPin, kPwmRange - gb::clampBrightness(pct));
}

void displayBegin(uint8_t brightnessPct) {
  analogWriteRange(kPwmRange);
  displaySetBrightness(0);  // keep dark until the controller is initialised
  tft.init();
  tft.invertDisplay(true);
  tft.setSwapBytes(true);
  tft.fillScreen(TFT_BLACK);
  TJpgDec.setJpgScale(1);
  TJpgDec.setCallback(tftOutput);
  displaySetBrightness(brightnessPct);
}

bool displayJpeg(const uint8_t* data, size_t len) {
  return TJpgDec.drawJpg(0, 0, data, len) == JDR_OK;
}

void displayStatus(const char* title, const char* const* lines, size_t n) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.drawString(title, 8, 8, 4);
  int y = 48;
  for (size_t i = 0; i < n; i++) {
    tft.drawString(lines[i], 8, y, 2);
    y += 20;
  }
}
