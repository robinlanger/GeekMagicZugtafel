// Vendored TJpgDec with our configuration (RGB565, no scaling, JD_FASTDECODE 1) and
// the static work-pool size used by src/display.cpp.
#include <unity.h>

#include <cstring>
#include <vector>

#include "fixtures.h"
#include "poll_timing.h"
#include "tjpgd.h"

void setUp() {}
void tearDown() {}

namespace {
struct Source {
  const uint8_t* data;
  size_t len;
  size_t pos;
};

std::vector<uint16_t> frame;

size_t input(JDEC* jd, uint8_t* buf, size_t n) {
  auto* s = static_cast<Source*>(jd->device);
  if (n > s->len - s->pos) n = s->len - s->pos;
  if (buf) std::memcpy(buf, s->data + s->pos, n);
  s->pos += n;
  return n;
}

int output(JDEC*, void* bitmap, JRECT* r) {
  const auto* px = static_cast<const uint16_t*>(bitmap);
  for (int y = r->top; y <= r->bottom; ++y)
    for (int x = r->left; x <= r->right; ++x) frame[y * 240 + x] = *px++;
  return 1;
}

alignas(4) uint8_t pool[gb::kJpegPoolBytes];

JRESULT decode(const uint8_t* data, size_t len, size_t poolBytes) {
  frame.assign(240 * 240, 0);
  Source src{data, len, 0};
  JDEC jd;
  JRESULT rc = jd_prepare(&jd, input, pool, poolBytes, &src);
  if (rc != JDR_OK) return rc;
  if (jd.width != 240 || jd.height != 240) return JDR_FMT1;
  return jd_decomp(&jd, output, 0);
}

void assertColor(int x, int y, int r5, int g6, int b5) {
  uint16_t p = frame[y * 240 + x];
  TEST_ASSERT_INT_WITHIN(2, r5, p >> 11);
  TEST_ASSERT_INT_WITHIN(3, g6, (p >> 5) & 0x3F);
  TEST_ASSERT_INT_WITHIN(2, b5, p & 0x1F);
}
}  // namespace

void test_server_style_jpeg_decodes_with_pool() {
  TEST_ASSERT_EQUAL(JDR_OK, decode(kServerStyle, sizeof(kServerStyle), sizeof(pool)));
  assertColor(60, 60, 31, 0, 0);    // red square
  assertColor(170, 170, 0, 0, 31);  // blue square
}

void test_standard_tables_fit_pool() {
  TEST_ASSERT_EQUAL(JDR_OK, decode(kStdTables444, sizeof(kStdTables444), sizeof(pool)));
  assertColor(60, 60, 31, 0, 0);
  TEST_ASSERT_EQUAL(JDR_OK, decode(kStdTables420, sizeof(kStdTables420), sizeof(pool)));
  assertColor(170, 170, 0, 0, 31);
}

void test_too_small_pool_is_reported() {
  TEST_ASSERT_EQUAL(JDR_MEM1, decode(kServerStyle, sizeof(kServerStyle), 1024));
}

void test_truncated_jpeg_fails_cleanly() {
  TEST_ASSERT_NOT_EQUAL(JDR_OK, decode(kServerStyle, sizeof(kServerStyle) / 2, sizeof(pool)));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_server_style_jpeg_decodes_with_pool);
  RUN_TEST(test_standard_tables_fit_pool);
  RUN_TEST(test_too_small_pool_is_reported);
  RUN_TEST(test_truncated_jpeg_fails_cleanly);
  return UNITY_END();
}
