#pragma once
// Frame protocol client (spec 5.2): GET <server>/api/v1/frame?id=<chip id>&fw=<version>.
// Normal mode only; safe mode never calls into this file.
#include <Arduino.h>

#include "frame_poll.h"

struct FrameResult {
  int status;               // HTTP status, HTTPClient error (< 0) or gb::kErr*
  size_t len;               // body bytes in frameData() (status 200 only)
  char etag[gb::kEtagCap];  // ETag of a 200 response ("" if absent or too long)
  int nextIn;               // X-Next-In seconds, -1 if absent/malformed
};

// One blocking request (connect/read timeout 8 s each, body read deadline 8 s).
// etag may be "" (no If-None-Match). On status 200 the JPEG is in frameData().
FrameResult fetchFrame(const char* serverUrl, const char* etag);
const uint8_t* frameData();
