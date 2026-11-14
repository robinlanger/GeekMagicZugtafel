#include <unity.h>

#include <cstring>
#include <string>

#include "boot_guard.h"
#include "frame_poll.h"
#include "ota_check.h"
#include "ota_flow.h"
#include "poll_timing.h"
#include "safe_policy.h"
#include "settings.h"
#include "web_util.h"

using namespace gb;

void setUp() {}
void tearDown() {}

void test_boot_fresh_magic() {
  BootDecision d = onBoot({0xDEADBEEF, 7});
  TEST_ASSERT_EQUAL_HEX32(kBootMagic, d.next.magic);
  TEST_ASSERT_EQUAL_UINT8(1, d.next.failed);
  TEST_ASSERT_FALSE(d.safeMode);
}

void test_boot_third_failure_enters_safe() {
  for (uint8_t f = 0; f < 3; ++f) {
    BootDecision d = onBoot({kBootMagic, f});
    TEST_ASSERT_FALSE(d.safeMode);
    TEST_ASSERT_EQUAL_UINT8(f + 1, d.next.failed);
  }
  TEST_ASSERT_TRUE(onBoot({kBootMagic, 3}).safeMode);
  BootDecision cap = onBoot({kBootMagic, 255});
  TEST_ASSERT_TRUE(cap.safeMode);
  TEST_ASSERT_EQUAL_UINT8(255, cap.next.failed);
}

void test_boot_healthy_resets() {
  BootState s = markHealthy();
  TEST_ASSERT_EQUAL_HEX32(kBootMagic, s.magic);
  TEST_ASSERT_EQUAL_UINT8(0, s.failed);
}

void test_is_healthy_needs_all_three() {
  TEST_ASSERT_TRUE(isHealthy(60000, true, true));
  TEST_ASSERT_FALSE(isHealthy(59999, true, true));
  TEST_ASSERT_FALSE(isHealthy(60000, false, true));
  TEST_ASSERT_FALSE(isHealthy(60000, true, false));
}

void test_next_delay_success_clamped() {
  TEST_ASSERT_EQUAL_UINT32(2000, nextDelayMs(true, 0, 0));
  TEST_ASSERT_EQUAL_UINT32(30000, nextDelayMs(true, 45, 0));
  TEST_ASSERT_EQUAL_UINT32(10000, nextDelayMs(true, -1, 0));
}

void test_next_delay_backoff() {
  TEST_ASSERT_EQUAL_UINT32(2000, nextDelayMs(false, -1, 1));
  TEST_ASSERT_EQUAL_UINT32(4000, nextDelayMs(false, -1, 2));
  TEST_ASSERT_EQUAL_UINT32(30000, nextDelayMs(false, -1, 5));
  TEST_ASSERT_EQUAL_UINT32(30000, nextDelayMs(false, -1, 255));
}

void test_show_offline_at_120s() {
  TEST_ASSERT_FALSE(showOffline(119999));
  TEST_ASSERT_TRUE(showOffline(120000));
}

void test_accept_frame_length() {
  TEST_ASSERT_FALSE(acceptFrameLength(0));
  TEST_ASSERT_FALSE(acceptFrameLength(-1));
  TEST_ASSERT_TRUE(acceptFrameLength(1));
  TEST_ASSERT_TRUE(acceptFrameLength(24576));
  TEST_ASSERT_FALSE(acceptFrameLength(24577));
}

void test_normalize_server_url_adds_scheme_and_strips_slash() {
  std::string err;
  auto r = normalizeServerUrl(" homeserver:8080/ ", &err);
  TEST_ASSERT_TRUE(r.has_value());
  TEST_ASSERT_EQUAL_STRING("http://homeserver:8080", r->c_str());
  auto r2 = normalizeServerUrl("http://a.lan//", &err);
  TEST_ASSERT_EQUAL_STRING("http://a.lan", r2->c_str());
}

void test_normalize_server_url_rejects_https() {
  std::string err;
  TEST_ASSERT_FALSE(normalizeServerUrl("https://x.lan", &err).has_value());
  TEST_ASSERT_EQUAL_STRING("https_unsupported", err.c_str());
}

void test_normalize_server_url_rejects_empty_host() {
  std::string err;
  TEST_ASSERT_FALSE(normalizeServerUrl("http://", &err).has_value());
  TEST_ASSERT_FALSE(normalizeServerUrl("   ", &err).has_value());
  TEST_ASSERT_FALSE(normalizeServerUrl("http://:8080", &err).has_value());
}

void test_valid_password() {
  TEST_ASSERT_FALSE(validPassword("1234567"));
  TEST_ASSERT_TRUE(validPassword("12345678"));
  TEST_ASSERT_EQUAL_UINT8(5, clampBrightness(0));
  TEST_ASSERT_EQUAL_UINT8(100, clampBrightness(500));
  TEST_ASSERT_EQUAL_UINT8(42, clampBrightness(42));
}

void test_md5_hex() {
  TEST_ASSERT_TRUE(isValidMd5Hex("d41d8cd98f00b204e9800998ecf8427e"));
  TEST_ASSERT_TRUE(isValidMd5Hex("D41D8CD98F00B204E9800998ECF8427E"));
  TEST_ASSERT_FALSE(isValidMd5Hex("d41d8cd98f00b204e9800998ecf8427"));
  TEST_ASSERT_FALSE(isValidMd5Hex("g41d8cd98f00b204e9800998ecf8427e"));
}

void test_image_magic() {
  const uint8_t ok[] = {0xE9, 0x03, 0x02, 0x40};
  const uint8_t bad[] = {0x7F, 0x45, 0x4C, 0x46};
  TEST_ASSERT_TRUE(looksLikeEsp8266Image(ok, 4));
  TEST_ASSERT_FALSE(looksLikeEsp8266Image(ok, 3));
  TEST_ASSERT_FALSE(looksLikeEsp8266Image(bad, 4));
  TEST_ASSERT_TRUE(fitsOta(1000, 1000));
  TEST_ASSERT_FALSE(fitsOta(1001, 1000));
}

void test_settings_roundtrip_with_escapes() {
  Settings s;
  TEST_ASSERT_TRUE(applyServerUrl(s, "homeserver:8080/", nullptr));
  TEST_ASSERT_TRUE(applyPassword(s, "pa\"ss\\w:rd", nullptr));
  s.brightness = 42;
  std::string text = encodeSettings(s);
  TEST_ASSERT_EQUAL_STRING(
      "{\"server_url\":\"http://homeserver:8080\",\"update_password\":\"pa\\\"ss\\\\w:rd\","
      "\"brightness\":42}\n",
      text.c_str());
  Settings back;
  TEST_ASSERT_TRUE(parseSettings(text, &back));
  TEST_ASSERT_EQUAL_STRING("http://homeserver:8080", back.serverUrl);
  TEST_ASSERT_EQUAL_STRING("pa\"ss\\w:rd", back.updatePassword);
  TEST_ASSERT_EQUAL_UINT8(42, back.brightness);
  TEST_ASSERT_TRUE(settingsComplete(back));
}

void test_settings_parse_tolerates_whitespace_unknown_keys_and_missing_brightness() {
  Settings s;
  TEST_ASSERT_TRUE(parseSettings(
      " {\n \"x\" : \"y\", \"n\": -3, \"update_password\" : \"abc\\u0041defgh\" ,"
      "\"server_url\":\"http://a.lan\"}\n",
      &s));
  TEST_ASSERT_EQUAL_STRING("abcAdefgh", s.updatePassword);
  TEST_ASSERT_EQUAL_STRING("http://a.lan", s.serverUrl);
  TEST_ASSERT_EQUAL_UINT8(kDefaultBrightness, s.brightness);
}

void test_settings_parse_rejects_corrupt_input() {
  const char* bad[] = {
      "",
      "{",
      "{\"server_url\":\"http://a.lan\"",
      "{\"server_url\":\"http://a.lan\"} trailing",
      "{\"server_url\":http}",
      "{\"brightness\":}",
      "{\"brightness\":1234567}",
      "{\"update_password\":\"ab\ncd\"}",
      "{\"update_password\":\"\\u0000\"}",
      "{\"update_password\":\"\\u00e9\"}",
      "{\"update_password\":\"\\q\"}",
      "{\"update_password\":\"0123456789012345678901234567890123\"}",
      "[1]",
  };
  for (const char* b : bad) {
    Settings s;
    s.brightness = 7;
    TEST_ASSERT_FALSE_MESSAGE(parseSettings(b, &s), b);
    TEST_ASSERT_EQUAL_UINT8(7, s.brightness);  // untouched on failure
  }
}

void test_settings_parse_clamps_brightness() {
  Settings s;
  TEST_ASSERT_TRUE(parseSettings("{\"brightness\":0}", &s));
  TEST_ASSERT_EQUAL_UINT8(5, s.brightness);
  TEST_ASSERT_TRUE(parseSettings("{\"brightness\":900}", &s));
  TEST_ASSERT_EQUAL_UINT8(100, s.brightness);
}

void test_settings_defaults_incomplete() {
  Settings s;
  TEST_ASSERT_EQUAL_STRING("", s.serverUrl);
  TEST_ASSERT_EQUAL_STRING("", s.updatePassword);
  TEST_ASSERT_EQUAL_UINT8(kDefaultBrightness, s.brightness);
  TEST_ASSERT_FALSE(settingsComplete(s));
  applyServerUrl(s, "a.lan", nullptr);
  TEST_ASSERT_FALSE(settingsComplete(s));
  applyPassword(s, "12345678", nullptr);
  TEST_ASSERT_TRUE(settingsComplete(s));
}

void test_apply_server_url_errors_leave_value() {
  Settings s;
  applyServerUrl(s, "a.lan", nullptr);
  std::string err;
  TEST_ASSERT_FALSE(applyServerUrl(s, "https://x", &err));
  TEST_ASSERT_EQUAL_STRING("https_unsupported", err.c_str());
  TEST_ASSERT_FALSE(applyServerUrl(s, "http://" + std::string(90, 'a'), &err));
  TEST_ASSERT_EQUAL_STRING("too_long", err.c_str());
  TEST_ASSERT_TRUE(applyServerUrl(s, "http://" + std::string(88, 'a'), &err));  // 95 chars fits
  TEST_ASSERT_FALSE(applyServerUrl(s, "", &err));
  TEST_ASSERT_EQUAL_STRING("empty_host", err.c_str());
  TEST_ASSERT_EQUAL_UINT(95, std::string(s.serverUrl).size());
}

void test_apply_password_rules() {
  Settings s;
  std::string err;
  TEST_ASSERT_FALSE(applyPassword(s, "short", &err));
  TEST_ASSERT_EQUAL_STRING("too_short", err.c_str());
  TEST_ASSERT_FALSE(applyPassword(s, std::string(33, 'x'), &err));
  TEST_ASSERT_EQUAL_STRING("too_long", err.c_str());
  TEST_ASSERT_FALSE(applyPassword(s, "abcdefg\xc3\xa9", &err));
  TEST_ASSERT_EQUAL_STRING("invalid_chars", err.c_str());
  TEST_ASSERT_FALSE(applyPassword(s, "abcdefgh\t", &err));
  TEST_ASSERT_EQUAL_STRING("", s.updatePassword);
  TEST_ASSERT_TRUE(applyPassword(s, std::string(32, '~'), &err));
  TEST_ASSERT_EQUAL_UINT(32, std::string(s.updatePassword).size());
}

void test_prefers_german() {
  TEST_ASSERT_TRUE(prefersGerman("de"));
  TEST_ASSERT_TRUE(prefersGerman("de-DE,de;q=0.9,en;q=0.8"));
  TEST_ASSERT_TRUE(prefersGerman(" DE-at"));
  TEST_ASSERT_FALSE(prefersGerman("en-US,de;q=0.9"));
  TEST_ASSERT_FALSE(prefersGerman(""));
  TEST_ASSERT_FALSE(prefersGerman(nullptr));
  TEST_ASSERT_FALSE(prefersGerman("dex"));
}

void test_html_escape() {
  TEST_ASSERT_EQUAL_STRING("a&amp;b&lt;c&gt;&quot;d&#39;", htmlEscape("a&b<c>\"d'").c_str());
}

void test_origin_allowed() {
  TEST_ASSERT_TRUE(originAllowed("", "192.168.1.5"));
  TEST_ASSERT_TRUE(originAllowed("http://192.168.1.5", "192.168.1.5"));
  TEST_ASSERT_TRUE(originAllowed("HTTP://Box.lan", "box.lan"));
  TEST_ASSERT_FALSE(originAllowed("http://evil.example", "192.168.1.5"));
  TEST_ASSERT_FALSE(originAllowed("null", "192.168.1.5"));
  TEST_ASSERT_FALSE(originAllowed("http://192.168.1.5", ""));
}

void test_ota_begin_size() {
  TEST_ASSERT_EQUAL_UINT(0, otaBeginSize(0));
  TEST_ASSERT_EQUAL_UINT(0, otaBeginSize(0x1000));
  TEST_ASSERT_EQUAL_UINT(0x1000, otaBeginSize(0x2FFF));
  TEST_ASSERT_EQUAL_UINT(0x7A000, otaBeginSize(0x7B000));
}

namespace {
const OtaStartChecks kGood{true, true, true, true, true};

// Drives one successful upload part up to (not including) Update.end().
void uploadUntilEnd(OtaFlow& f) {
  f.onFileStart(kGood);
  TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::BeginAndWrite);
  f.onBegin(true);
  f.onWrite(true, false);
  TEST_ASSERT_TRUE(f.onChunk(false) == OtaFlow::Chunk::Write);  // later chunks: no header check
  f.onWrite(true, false);
  TEST_ASSERT_TRUE(f.onFileEnd() == OtaFlow::End::Finish);
}
}  // namespace

void test_ota_flow_success_commits_at_file_end() {
  OtaFlow f;
  uploadUntilEnd(f);
  TEST_ASSERT_TRUE(f.onFinished(true, OtaError::None));
  TEST_ASSERT_TRUE(f.committed());
  TEST_ASSERT_FALSE(f.mayDiscard());
  TEST_ASSERT_EQUAL(200, f.response().code);
}

void test_ota_flow_abort_after_commit_keeps_commit_and_success() {
  OtaFlow f;
  uploadUntilEnd(f);
  f.onFinished(true, OtaError::None);
  f.onAborted();  // client disconnected after the final boundary
  TEST_ASSERT_TRUE(f.committed());
  TEST_ASSERT_FALSE(f.mayDiscard());
  TEST_ASSERT_EQUAL(200, f.response().code);
}

void test_ota_flow_second_part_after_commit_never_touches_flash() {
  OtaFlow f;
  uploadUntilEnd(f);
  f.onFinished(true, OtaError::None);
  f.onFileStart(kGood);  // second file part in the same request
  TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_TRUE(f.onFileEnd() == OtaFlow::End::Skip);
  TEST_ASSERT_FALSE(f.mayDiscard());
  TEST_ASSERT_EQUAL(200, f.response().code);  // the committed image stands
}

void test_ota_flow_later_requests_refused_after_commit() {
  OtaFlow f;
  uploadUntilEnd(f);
  f.onFinished(true, OtaError::None);
  f.endRequest();
  TEST_ASSERT_TRUE(f.committed());
  f.onFileStart(kGood);
  TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_TRUE(f.onFileEnd() == OtaFlow::End::Skip);
  TEST_ASSERT_FALSE(f.mayDiscard());
  TEST_ASSERT_TRUE(f.error() == OtaError::Committed);
  TEST_ASSERT_EQUAL(400, f.response().code);
}

void test_ota_flow_unauthorized_never_writes() {
  OtaFlow f;
  f.onFileStart({true, false, true, true, true});
  TEST_ASSERT_FALSE(f.authorized());
  TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_TRUE(f.onFileEnd() == OtaFlow::End::Skip);
  TEST_ASSERT_EQUAL(401, f.response().code);
  OtaFlow g;
  g.onFileStart({false, true, true, true, true});
  TEST_ASSERT_TRUE(g.onChunk(true) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_EQUAL(403, g.response().code);
}

void test_ota_flow_start_checks_reject_before_flash() {
  const OtaStartChecks bad[] = {{true, true, false, true, true},
                                {true, true, true, false, true},
                                {true, true, true, true, false}};
  const OtaError expect[] = {OtaError::Field, OtaError::Md5, OtaError::TooLarge};
  for (int i = 0; i < 3; ++i) {
    OtaFlow f;
    f.onFileStart(bad[i]);
    TEST_ASSERT_TRUE(f.authorized());
    TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::Skip);
    TEST_ASSERT_TRUE(f.error() == expect[i]);
    TEST_ASSERT_EQUAL(400, f.response().code);
    TEST_ASSERT_TRUE(f.mayDiscard());
  }
}

void test_ota_flow_not_an_image_rejected_on_first_chunk() {
  OtaFlow f;
  f.onFileStart(kGood);
  TEST_ASSERT_TRUE(f.onChunk(false) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_TRUE(f.error() == OtaError::NotImage);
  TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::Skip);  // stays failed
  TEST_ASSERT_TRUE(f.onFileEnd() == OtaFlow::End::Skip);
  TEST_ASSERT_EQUAL(400, f.response().code);
}

void test_ota_flow_md5_mismatch_and_errors_discard() {
  OtaFlow f;
  uploadUntilEnd(f);
  TEST_ASSERT_FALSE(f.onFinished(false, OtaError::Md5Mismatch));
  TEST_ASSERT_FALSE(f.committed());
  TEST_ASSERT_TRUE(f.mayDiscard());
  TEST_ASSERT_EQUAL(400, f.response().code);
  TEST_ASSERT_EQUAL_STRING("md5 mismatch", otaErrorText(f.response().error));

  OtaFlow w;
  w.onFileStart(kGood);
  w.onChunk(true);
  w.onBegin(true);
  w.onWrite(false, false);
  TEST_ASSERT_TRUE(w.onChunk(true) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_EQUAL(500, w.response().code);

  OtaFlow b;
  b.onFileStart(kGood);
  b.onChunk(true);
  b.onBegin(false);
  TEST_ASSERT_EQUAL(500, b.response().code);

  OtaFlow a;
  a.onFileStart(kGood);
  a.onChunk(true);
  a.onBegin(true);
  a.onAborted();
  TEST_ASSERT_TRUE(a.error() == OtaError::Aborted);
  TEST_ASSERT_TRUE(a.mayDiscard());
}

void test_ota_flow_empty_and_second_part_after_failure() {
  OtaFlow f;
  f.onFileStart(kGood);
  TEST_ASSERT_TRUE(f.onFileEnd() == OtaFlow::End::Skip);
  TEST_ASSERT_TRUE(f.error() == OtaError::Empty);
  f.onFileStart(kGood);  // second part cannot reset the failure
  TEST_ASSERT_TRUE(f.onChunk(true) == OtaFlow::Chunk::Skip);
  TEST_ASSERT_TRUE(f.error() == OtaError::Empty);
  f.endRequest();
  TEST_ASSERT_FALSE(f.started());
  TEST_ASSERT_FALSE(f.failed());
  uploadUntilEnd(f);  // a fresh request works again
  TEST_ASSERT_TRUE(f.onFinished(true, OtaError::None));
}

// ---- Task 13: health latch, safe-mode policy, frame poll state ----

void test_health_latch_marks_exactly_once() {
  HealthLatch h;
  TEST_ASSERT_FALSE(h.shouldMark(59999, true, true));
  TEST_ASSERT_FALSE(h.shouldMark(60000, false, true));
  TEST_ASSERT_FALSE(h.shouldMark(60000, true, false));
  TEST_ASSERT_FALSE(h.marked());
  TEST_ASSERT_TRUE(h.shouldMark(60000, true, true));
  TEST_ASSERT_TRUE(h.marked());
  TEST_ASSERT_FALSE(h.shouldMark(60001, true, true));
  TEST_ASSERT_FALSE(h.shouldMark(900000, true, true));
}

void test_safe_mode_portal_only_without_valid_password() {
  Settings s;  // missing/corrupt settings file -> defaults
  TEST_ASSERT_TRUE(safeModeNeedsPortal(s));
  std::string err;
  TEST_ASSERT_TRUE(applyPassword(s, "longenough", &err));
  // URL is irrelevant in safe mode: a valid password is enough to accept updates.
  TEST_ASSERT_FALSE(safeModeNeedsPortal(s));
  TEST_ASSERT_TRUE(applyServerUrl(s, "homeserver:8080", &err));
  TEST_ASSERT_FALSE(safeModeNeedsPortal(s));
  strcpy(s.updatePassword, "short");  // corrupt/invalid stored password
  TEST_ASSERT_TRUE(safeModeNeedsPortal(s));
}

void test_safe_mode_ap_fallback_after_connect_timeout() {
  TEST_ASSERT_FALSE(safeModeApFallback(false, kSafeModeConnectMs - 1));
  TEST_ASSERT_TRUE(safeModeApFallback(false, kSafeModeConnectMs));
  TEST_ASSERT_FALSE(safeModeApFallback(true, kSafeModeConnectMs * 10));
}

void test_parse_next_in() {
  TEST_ASSERT_EQUAL_INT(-1, parseNextIn(nullptr));
  TEST_ASSERT_EQUAL_INT(-1, parseNextIn(""));
  TEST_ASSERT_EQUAL_INT(15, parseNextIn("15"));
  TEST_ASSERT_EQUAL_INT(15, parseNextIn(" 15 "));
  TEST_ASSERT_EQUAL_INT(0, parseNextIn("0"));
  TEST_ASSERT_EQUAL_INT(-1, parseNextIn("-3"));
  TEST_ASSERT_EQUAL_INT(-1, parseNextIn("1.5"));
  TEST_ASSERT_EQUAL_INT(-1, parseNextIn("abc"));
  TEST_ASSERT_EQUAL_INT(9999, parseNextIn("99999999999999999999"));  // saturates, clamped later
  TEST_ASSERT_EQUAL_UINT32(30000, nextDelayMs(true, parseNextIn("99999999999999999999"), 0));
}

void test_store_etag() {
  char e[kEtagCap];
  TEST_ASSERT_TRUE(storeEtag(e, "\"abc\""));
  TEST_ASSERT_EQUAL_STRING("\"abc\"", e);
  std::string max(kEtagCap - 1, 'x');
  TEST_ASSERT_TRUE(storeEtag(e, max.c_str()));
  TEST_ASSERT_EQUAL_STRING(max.c_str(), e);
  std::string tooLong(kEtagCap, 'y');
  TEST_ASSERT_FALSE(storeEtag(e, tooLong.c_str()));  // never keep a truncated tag
  TEST_ASSERT_EQUAL_STRING("", e);
  TEST_ASSERT_FALSE(storeEtag(e, nullptr));
  TEST_ASSERT_EQUAL_STRING("", e);
}

void test_frame_error_text() {
  char b[kErrorTextCap];
  frameErrorText(500, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("HTTP 500", b);
  frameErrorText(-1, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("connection failed", b);
  frameErrorText(-11, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("read timeout", b);
  frameErrorText(kErrFrameLength, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("bad frame size", b);
  frameErrorText(kErrBodyRead, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("frame incomplete", b);
  frameErrorText(kErrDecode, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("bad JPEG", b);
  frameErrorText(kErrNoWifi, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("no Wi-Fi", b);
  frameErrorText(-7, b, sizeof(b));
  TEST_ASSERT_EQUAL_STRING("network error -7", b);
  char tiny[4];
  frameErrorText(500, tiny, sizeof(tiny));
  TEST_ASSERT_EQUAL_STRING("HTT", tiny);
}

void test_poller_success_uses_next_in_and_resets_failures() {
  FramePoller p;
  p.begin(1000);
  PollOutcome o = p.onFailure(-1, 2000);
  TEST_ASSERT_EQUAL_UINT32(2000, o.delayMs);
  o = p.onFailure(-1, 4000);
  TEST_ASSERT_EQUAL_UINT32(4000, o.delayMs);
  TEST_ASSERT_EQUAL_UINT8(2, p.failures());
  o = p.onSuccess(12, 8000);
  TEST_ASSERT_EQUAL_UINT32(12000, o.delayMs);
  TEST_ASSERT_FALSE(o.drawOffline);
  TEST_ASSERT_FALSE(o.clearEtag);
  TEST_ASSERT_EQUAL_UINT8(0, p.failures());
  TEST_ASSERT_EQUAL_UINT32(2000, p.onFailure(-1, 9000).delayMs);  // backoff restarts
}

void test_poller_offline_after_120s_since_boot_or_last_success() {
  FramePoller p;
  p.begin(5000);  // never succeeded: the clock starts at begin()
  TEST_ASSERT_FALSE(p.onFailure(-1, 5000 + 119999).drawOffline);
  PollOutcome o = p.onFailure(-1, 5000 + 120000);
  TEST_ASSERT_TRUE(o.drawOffline);
  TEST_ASSERT_TRUE(o.clearEtag);  // screen no longer shows the frame of the stored ETag
  TEST_ASSERT_TRUE(p.offline());
  // Same error again: no redraw (no flicker every poll).
  o = p.onFailure(-1, 5000 + 150000);
  TEST_ASSERT_FALSE(o.drawOffline);
  TEST_ASSERT_FALSE(o.clearEtag);
  // Different error while offline: redraw with the new text.
  TEST_ASSERT_TRUE(p.onFailure(500, 5000 + 180000).drawOffline);
  TEST_ASSERT_FALSE(p.onFailure(500, 5000 + 210000).drawOffline);
  // Recovery leaves offline; a later outage needs another full 120 s.
  p.onSuccess(10, 300000);
  TEST_ASSERT_FALSE(p.offline());
  TEST_ASSERT_FALSE(p.onFailure(-1, 300000 + 119999).drawOffline);
  TEST_ASSERT_TRUE(p.onFailure(-1, 300000 + 120000).drawOffline);
}

void test_poller_millis_wraparound() {
  FramePoller p;
  p.begin(0xFFFFF000u);
  TEST_ASSERT_FALSE(p.onFailure(-1, 0x00001000u).drawOffline);  // 8 KB ms later, wrapped
  TEST_ASSERT_TRUE(p.onFailure(-1, 0xFFFFF000u + 120000u).drawOffline);
}

void test_poller_decode_error_clears_etag() {
  FramePoller p;
  p.begin(0);
  PollOutcome o = p.onFailure(kErrDecode, 1000);
  TEST_ASSERT_TRUE(o.clearEtag);  // a partial draw must be replaced by a full 200 next time
  TEST_ASSERT_FALSE(o.drawOffline);
  TEST_ASSERT_FALSE(p.onFailure(-1, 2000).clearEtag);  // the last good frame still stands
}

void test_poller_failure_count_saturates() {
  FramePoller p;
  p.begin(0);
  for (int i = 0; i < 300; ++i) p.onFailure(-1, 1000);
  TEST_ASSERT_EQUAL_UINT8(255, p.failures());
  TEST_ASSERT_EQUAL_UINT32(30000, p.onFailure(-1, 1000).delayMs);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_boot_fresh_magic);
  RUN_TEST(test_boot_third_failure_enters_safe);
  RUN_TEST(test_boot_healthy_resets);
  RUN_TEST(test_is_healthy_needs_all_three);
  RUN_TEST(test_next_delay_success_clamped);
  RUN_TEST(test_next_delay_backoff);
  RUN_TEST(test_show_offline_at_120s);
  RUN_TEST(test_accept_frame_length);
  RUN_TEST(test_normalize_server_url_adds_scheme_and_strips_slash);
  RUN_TEST(test_normalize_server_url_rejects_https);
  RUN_TEST(test_normalize_server_url_rejects_empty_host);
  RUN_TEST(test_valid_password);
  RUN_TEST(test_md5_hex);
  RUN_TEST(test_image_magic);
  RUN_TEST(test_settings_roundtrip_with_escapes);
  RUN_TEST(test_settings_parse_tolerates_whitespace_unknown_keys_and_missing_brightness);
  RUN_TEST(test_settings_parse_rejects_corrupt_input);
  RUN_TEST(test_settings_parse_clamps_brightness);
  RUN_TEST(test_settings_defaults_incomplete);
  RUN_TEST(test_apply_server_url_errors_leave_value);
  RUN_TEST(test_apply_password_rules);
  RUN_TEST(test_prefers_german);
  RUN_TEST(test_html_escape);
  RUN_TEST(test_origin_allowed);
  RUN_TEST(test_ota_begin_size);
  RUN_TEST(test_ota_flow_success_commits_at_file_end);
  RUN_TEST(test_ota_flow_abort_after_commit_keeps_commit_and_success);
  RUN_TEST(test_ota_flow_second_part_after_commit_never_touches_flash);
  RUN_TEST(test_ota_flow_later_requests_refused_after_commit);
  RUN_TEST(test_ota_flow_unauthorized_never_writes);
  RUN_TEST(test_ota_flow_start_checks_reject_before_flash);
  RUN_TEST(test_ota_flow_not_an_image_rejected_on_first_chunk);
  RUN_TEST(test_ota_flow_md5_mismatch_and_errors_discard);
  RUN_TEST(test_ota_flow_empty_and_second_part_after_failure);
  RUN_TEST(test_health_latch_marks_exactly_once);
  RUN_TEST(test_safe_mode_portal_only_without_valid_password);
  RUN_TEST(test_safe_mode_ap_fallback_after_connect_timeout);
  RUN_TEST(test_parse_next_in);
  RUN_TEST(test_store_etag);
  RUN_TEST(test_frame_error_text);
  RUN_TEST(test_poller_success_uses_next_in_and_resets_failures);
  RUN_TEST(test_poller_offline_after_120s_since_boot_or_last_success);
  RUN_TEST(test_poller_millis_wraparound);
  RUN_TEST(test_poller_decode_error_clears_etag);
  RUN_TEST(test_poller_failure_count_saturates);
  return UNITY_END();
}
