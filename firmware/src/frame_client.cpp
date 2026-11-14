#include "frame_client.h"

#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>

#include "poll_timing.h"
#include "version.h"

namespace {

constexpr uint16_t kTimeoutMs = 8000;

// Allocated once, never on the heap: the largest frame the server may send.
uint8_t frameBuf[gb::kMaxFrameBytes];

// Reads exactly len bytes into frameBuf before the deadline. yield()s while waiting.
bool readBody(WiFiClient& s, size_t len) {
  size_t got = 0;
  const uint32_t start = millis();
  while (got < len && millis() - start < kTimeoutMs) {
    const int avail = s.available();
    if (avail > 0) {
      const size_t want = len - got;
      const int n = s.read(frameBuf + got, static_cast<size_t>(avail) < want ? avail : want);
      if (n > 0) got += static_cast<size_t>(n);
    } else if (!s.connected()) {
      break;
    } else {
      delay(1);  // yields: feeds the watchdog and lets the TCP stack run
    }
  }
  return got == len;
}

}  // namespace

const uint8_t* frameData() { return frameBuf; }

FrameResult fetchFrame(const char* serverUrl, const char* etag) {
  FrameResult r{gb::kErrBadUrl, 0, "", -1};
  char url[192];
  const int n = snprintf(url, sizeof(url), "%s/api/v1/frame?id=%06x&fw=%s", serverUrl,
                         static_cast<unsigned>(ESP.getChipId()), GB_VERSION);
  if (n <= 0 || static_cast<size_t>(n) >= sizeof(url)) return r;

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(kTimeoutMs);
  http.setReuse(false);
  if (!http.begin(client, url)) return r;
  const char* headers[] = {"ETag", "X-Next-In"};
  http.collectHeaders(headers, 2);
  if (etag != nullptr && etag[0] != '\0') http.addHeader(F("If-None-Match"), etag);

  r.status = http.GET();
  if (r.status > 0) r.nextIn = gb::parseNextIn(http.header("X-Next-In").c_str());
  if (r.status == HTTP_CODE_OK) {
    const int len = http.getSize();  // -1 without Content-Length (e.g. chunked)
    if (!gb::acceptFrameLength(len)) {
      r.status = gb::kErrFrameLength;
    } else if (!readBody(http.getStream(), static_cast<size_t>(len))) {
      r.status = gb::kErrBodyRead;
    } else {
      r.len = static_cast<size_t>(len);
      gb::storeEtag(r.etag, http.header("ETag").c_str());
    }
  }
  http.end();
  return r;
}
