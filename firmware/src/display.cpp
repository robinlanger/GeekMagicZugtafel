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

// Streaming source: never reads beyond len bytes; gives up at the deadline.
struct JpegSource {
  Stream* stream;
  size_t left;          // bytes of the body not consumed yet
  uint32_t startMs;
  uint32_t deadlineMs;  // overall budget for the whole body
  bool starved;         // stream ended or stalled before tjpgd got what it asked for
};

// Input callback: read (or skip, when buf is null) up to n bytes from the stream.
// Returns fewer than n only on failure; tjpgd then aborts with JDR_INP.
size_t jpegInput(JDEC* jd, uint8_t* buf, size_t n) {
  auto* src = static_cast<JpegSource*>(jd->device);
  if (n > src->left) n = src->left;
  uint8_t skip[64];
  size_t done = 0;
  while (done < n) {
    if (millis() - src->startMs >= src->deadlineMs) break;
    const int avail = src->stream->available();
    if (avail <= 0) {
      delay(0);  // yield: watchdog, TCP stack
      continue;
    }
    size_t want = n - done;
    if (want > static_cast<size_t>(avail)) want = static_cast<size_t>(avail);
    if (buf == nullptr && want > sizeof(skip)) want = sizeof(skip);
    const size_t got = src->stream->readBytes(buf != nullptr ? buf + done : skip, want);
    if (got == 0) break;
    done += got;
  }
  src->left -= done;
  if (done < n) src->starved = true;
  return done;
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

void displaySetBacklight(uint8_t pct) {
  // Backlight is active-low: duty = max - percentage.
  analogWrite(kBacklightPin, kPwmRange - (pct > 100 ? 100 : pct));
}

void displaySetBrightness(uint8_t pct) { displaySetBacklight(gb::clampBrightness(pct)); }

void displayBegin(uint8_t brightnessPct) {
  analogWriteRange(kPwmRange);
  displaySetBacklight(0);  // keep dark until the controller is initialised
  tft.init();
  tft.invertDisplay(true);
  tft.setSwapBytes(true);  // TJpgDec emits native-endian RGB565
  tft.fillScreen(TFT_BLACK);
  displaySetBrightness(brightnessPct);
}

JpegStreamResult displayJpegStream(Stream& stream, size_t len, uint32_t deadlineMs) {
  JpegSource src{&stream, len, millis(), deadlineMs, false};
  JDEC jd;
  JRESULT rc = jd_prepare(&jd, jpegInput, jpegPool, sizeof(jpegPool), &src);
  if (rc == JDR_OK) rc = jd_decomp(&jd, jpegOutput, 0);
  if (rc == JDR_OK || rc == JDR_INTR) return JpegStreamResult::Ok;  // INTR: below the visible area
  return src.starved ? JpegStreamResult::InputError : JpegStreamResult::DecodeError;
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
