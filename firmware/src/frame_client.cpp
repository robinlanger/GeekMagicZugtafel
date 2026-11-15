#include "frame_client.h"

#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>

#include "arduino_str.h"
#include "display.h"
#include "night.h"
#include "poll_timing.h"
#include "version.h"

namespace {
constexpr uint16_t kTimeoutMs = 8000;
}  // namespace

FrameResult fetchFrame(const char* serverUrl, const char* etag) {
  FrameResult r{gb::kErrBadUrl, 0, "", -1, -1};
  char url[192];
  const int n = snprintf(url, sizeof(url), "%s/api/v1/frame?id=%06x&fw=%s", serverUrl,
                         static_cast<unsigned>(ESP.getChipId()), gbVersion());
  if (n <= 0 || static_cast<size_t>(n) >= sizeof(url)) return r;

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(kTimeoutMs);
  http.setReuse(false);
  if (!http.begin(client, url)) return r;
  const char* headers[] = {"ETag", "X-Next-In", "X-Local-Time"};
  http.collectHeaders(headers, 3);
  if (etag != nullptr && etag[0] != '\0') http.addHeader(F("If-None-Match"), etag);

  r.status = http.GET();
  if (r.status > 0) {
    r.nextIn = gb::parseNextIn(strOrEmpty(http.header("X-Next-In")));
    r.localSec = gb::parseLocalTime(strOrEmpty(http.header("X-Local-Time")));
  }
  if (r.status == HTTP_CODE_OK) {
    const int len = http.getSize();  // -1 without Content-Length (e.g. chunked): rejected
    WiFiClient* stream = http.getStreamPtr();
    if (!gb::acceptFrameLength(len) || stream == nullptr) {
      r.status = gb::kErrFrameLength;
    } else {
      r.len = static_cast<size_t>(len);
      switch (displayJpegStream(*stream, r.len, kTimeoutMs)) {
        case JpegStreamResult::Ok:
          gb::storeEtag(r.etag, http.header("ETag").c_str());  // only after a full decode
          break;
        case JpegStreamResult::InputError:
          r.status = gb::kErrBodyRead;
          break;
        case JpegStreamResult::DecodeError:
          r.status = gb::kErrDecode;
          break;
      }
    }
  }
  http.end();
  return r;
}
