#include <unity.h>

#include <string>

#include "boot_guard.h"
#include "ota_check.h"
#include "poll_timing.h"
#include "settings.h"

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
  return UNITY_END();
}
