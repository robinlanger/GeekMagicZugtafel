#include "ota_flow.h"

namespace gb {

const char* otaErrorText(OtaError e) {
  switch (e) {
    case OtaError::None: return "ok";
    case OtaError::Origin: return "origin not allowed";
    case OtaError::Auth: return "unauthorized";
    case OtaError::Committed: return "an update is already staged, restarting";
    case OtaError::Field: return "expected exactly one file field named firmware";
    case OtaError::Md5: return "md5 missing or invalid (send md5 before firmware)";
    case OtaError::TooLarge: return "image too large";
    case OtaError::NotImage: return "not an ESP8266 image";
    case OtaError::Begin: return "Update.begin failed";
    case OtaError::Write: return "flash write failed";
    case OtaError::Md5Mismatch: return "md5 mismatch";
    case OtaError::Header: return "image header does not fit this device";
    case OtaError::Verify: return "verification failed";
    case OtaError::Aborted: return "upload aborted";
    case OtaError::Empty: return "empty or truncated image";
    case OtaError::Missing: return "firmware missing";
  }
  return "unknown error";
}

void OtaFlow::fail(OtaError e) {
  if (error_ == OtaError::None) error_ = e;  // first failure wins
}

void OtaFlow::onFileStart(const OtaStartChecks& c) {
  if (started_) {  // a second file part never gets a fresh start
    fail(OtaError::Field);
    return;
  }
  started_ = true;
  if (!c.originOk) return fail(OtaError::Origin);
  if (!c.authOk) return fail(OtaError::Auth);
  authorized_ = true;
  if (committed_) return fail(OtaError::Committed);
  if (!c.fieldOk) return fail(OtaError::Field);
  if (!c.md5Ok) return fail(OtaError::Md5);
  if (!c.fits) return fail(OtaError::TooLarge);
}

OtaFlow::Chunk OtaFlow::onChunk(bool imageOk) {
  if (!started_ || failed() || committedInRequest_ || committed_) return Chunk::Skip;
  if (begun_) return Chunk::Write;
  if (!imageOk) {
    fail(OtaError::NotImage);
    return Chunk::Skip;
  }
  return Chunk::BeginAndWrite;
}

void OtaFlow::onBegin(bool ok) {
  if (ok) {
    begun_ = true;
  } else {
    fail(OtaError::Begin);
  }
}

void OtaFlow::onWrite(bool ok, bool spaceError) {
  if (!ok) fail(spaceError ? OtaError::TooLarge : OtaError::Write);
}

OtaFlow::End OtaFlow::onFileEnd() {
  if (!started_ || failed() || committedInRequest_ || committed_) return End::Skip;
  if (!begun_) {
    fail(OtaError::Empty);
    return End::Skip;
  }
  return End::Finish;
}

bool OtaFlow::onFinished(bool ok, OtaError failure) {
  if (!ok) {
    fail(failure == OtaError::None ? OtaError::Verify : failure);
    return false;
  }
  committed_ = true;
  committedInRequest_ = true;
  return true;
}

void OtaFlow::onAborted() {
  if (!committedInRequest_) fail(OtaError::Aborted);
}

OtaResponse OtaFlow::response() const {
  if (committedInRequest_) return {200, OtaError::None};
  switch (error_) {
    case OtaError::Origin: return {403, error_};
    case OtaError::Auth: return {401, error_};
    case OtaError::Begin:
    case OtaError::Write:
    case OtaError::Header:
    case OtaError::Verify: return {500, error_};
    case OtaError::None: return {400, started_ ? OtaError::Aborted : OtaError::Missing};
    default: return {400, error_};
  }
}

void OtaFlow::endRequest() {
  const bool committed = committed_;
  *this = OtaFlow();
  committed_ = committed;
}

}  // namespace gb
