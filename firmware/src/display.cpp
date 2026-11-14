#include "display.h"

#include "poll_timing.h"
#include "settings.h"
#include "tjpgd.h"

namespace {
constexpr uint8_t kBacklightPin = 5;
constexpr int kPwmRange = 100;
constexpr int kHeight = 240;

TFT_eSPI tft;

// TJpgDec work pool: static, never heap (size verified by test_tjpgd).
alignas(4) uint8_t jpegPool[gb::kJpegPoolBytes];

struct JpegSource {
  const uint8_t* data;
  size_t len;
  size_t pos;
};

// Input callback: copy (or skip, when buf is null) up to n bytes from the memory buffer.
size_t jpegInput(JDEC* jd, uint8_t* buf, size_t n) {
  auto* src = static_cast<JpegSource*>(jd->device);
  const size_t left = src->len - src->pos;
  if (n > left) n = left;
  if (buf != nullptr) memcpy(buf, src->data + src->pos, n);
  src->pos += n;
  return n;
}

// Output callback: push one decoded RGB565 block; stop below the visible area.
int jpegOutput(JDEC*, void* bitmap, JRECT* rect) {
  if (rect->top >= kHeight) return 0;
  tft.pushImage(rect->left, rect->top, rect->right - rect->left + 1, rect->bottom - rect->top + 1,
                static_cast<uint16_t*>(bitmap));
  return 1;
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
  tft.setSwapBytes(true);  // TJpgDec emits native-endian RGB565
  tft.fillScreen(TFT_BLACK);
  displaySetBrightness(brightnessPct);
}

bool displayJpeg(const uint8_t* data, size_t len) {
  JpegSource src{data, len, 0};
  JDEC jd;
  if (jd_prepare(&jd, jpegInput, jpegPool, sizeof(jpegPool), &src) != JDR_OK) return false;
  const JRESULT rc = jd_decomp(&jd, jpegOutput, 0);
  return rc == JDR_OK || rc == JDR_INTR;  // INTR: stopped below the visible area
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
