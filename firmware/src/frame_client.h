#pragma once
// Frame protocol client (spec 5.2): GET <server>/api/v1/frame?id=<chip id>&fw=<version>.
// Normal mode only; safe mode never calls into this file.
#include <Arduino.h>

#include "frame_poll.h"

struct FrameResult {
  int status;               // 200 (frame drawn), 304, other HTTP status, HTTPClient error (< 0) or gb::kErr*
  size_t len;               // Content-Length of a 200 response
  char etag[gb::kEtagCap];  // ETag of a drawn 200 frame ("" if absent, too long or not drawn)
  int nextIn;               // X-Next-In seconds, -1 if absent/malformed
};

// One blocking request (connect/read timeout 8 s). A 200 body is stream-decoded straight
// to the display (no frame buffer) within an 8 s body deadline. Failures mid-body return
// gb::kErrBodyRead / gb::kErrDecode and leave a partially drawn frame.
FrameResult fetchFrame(const char* serverUrl, const char* etag);
