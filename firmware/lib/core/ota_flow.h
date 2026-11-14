#pragma once
#include <cstdint>

namespace gb {

enum class OtaError : uint8_t {
  None,
  Origin,       // 403
  Auth,         // 401
  Committed,    // an image is already staged; restart pending
  Field,        // wrong field name or more than one file part
  Md5,          // md5 missing/invalid at file start
  TooLarge,
  NotImage,     // first chunk is not an ESP8266 image
  Begin,        // Update.begin/setMD5 failed
  Write,        // flash write failed
  Md5Mismatch,
  Header,       // image header does not fit this device
  Verify,       // other Update.end() failure
  Aborted,      // client went away
  Empty,        // file part without data
  Missing,      // request without file part
};

struct OtaStartChecks {
  bool originOk;
  bool authOk;
  bool fieldOk;
  bool md5Ok;
  bool fits;
};

struct OtaResponse {
  int code;  // 200, 400, 401 (ask for credentials), 403 or 500
  OtaError error;
};

const char* otaErrorText(OtaError e);

// Decisions of the POST /update upload handler, free of Arduino types.
// The commit point is a successful Update.end(true) at file end: from then on the
// staged image (eboot copy command) must never be touched again in this boot, and
// the request reports success whatever events follow.
class OtaFlow {
 public:
  enum class Chunk : uint8_t { Skip, BeginAndWrite, Write };
  enum class End : uint8_t { Skip, Finish };

  void onFileStart(const OtaStartChecks& c);
  // imageOk: looksLikeEsp8266Image(chunk) (only consulted for the first chunk).
  Chunk onChunk(bool imageOk);
  void onBegin(bool ok);
  void onWrite(bool ok, bool spaceError);
  End onFileEnd();
  // Result of Update.end(true). Returns true exactly when this call commits.
  bool onFinished(bool ok, OtaError failure);
  void onAborted();

  // The caller may abort the Updater and clear the eboot command (false after a commit).
  bool mayDiscard() const { return !committed_; }
  bool failed() const { return error_ != OtaError::None; }
  bool authorized() const { return authorized_; }
  bool started() const { return started_; }
  bool committed() const { return committed_; }
  OtaError error() const { return error_; }
  // Response for the request once parsing is done (only meaningful when started()).
  OtaResponse response() const;
  // Clears per-request state; a commit stays for the rest of this boot.
  void endRequest();

 private:
  void fail(OtaError e);

  bool started_ = false;
  bool authorized_ = false;
  bool begun_ = false;
  bool committedInRequest_ = false;
  bool committed_ = false;
  OtaError error_ = OtaError::None;
};

}  // namespace gb
