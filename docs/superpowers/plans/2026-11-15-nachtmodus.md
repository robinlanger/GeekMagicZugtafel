# Nachtmodus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display is dimmed or fully dark in a user-set nightly time window, configured on the device web page.

**Architecture:** The server adds `X-Local-Time: HH:MM:SS` (configured timezone) to every frame response. The firmware keeps a local clock synced from that header and continued with `millis()`. A pure core function decides the effective backlight percentage. The main loop applies it whenever it changes.

**Tech Stack:** Python 3.12/FastAPI (server), PlatformIO Arduino ESP8266 + Unity native tests (firmware).

**Spec:** `docs/superpowers/specs/2026-11-15-nachtmodus-design.md`

## Global Constraints

- Night window: `night_start`, `night_end` in minutes since midnight (0–1439), `night_brightness` 0–100; defaults 0, 0, 0 (start == end → night mode off).
- Night active iff start ≠ end and start ≤ t < end (start < end) or t ≥ start || t < end (start > end). Start inclusive, end exclusive.
- Day brightness stays 5–100; 0 allowed only for night brightness.
- Unknown time (no valid header since boot) → day brightness.
- Safe mode ignores night mode.
- Settings JSON keys exactly `night_start`, `night_end`, `night_brightness`; a 0.1.0 settings file must load (missing keys → defaults).
- Device UI DE + EN; docs DE + EN in parity (`tools/check_docs_parity.py`).
- Firmware image must stay under `firmware/size-limit.txt`.
- Native tests: run on the Mac host (`cd firmware && pio test -e native`); ESP builds via `.superpowers/sdd/2026-11-14-glancebox/pio-docker.sh run -e ultra` (host toolchain is x86-only).

## Review Focus

1. Window across midnight (22:00–07:00) at 23:59, 00:00, 06:59, 07:00 → night, night, night, day.
2. `millis()` wraps after ~49.7 days → clock still correct (unsigned subtraction), no stuck night.
3. Header missing, garbage (`25:00:00`, `ab`, empty) or from an error frame → ignored, last good sync kept.
4. Saving settings on the web page at night must not light the display up until the next check; changing the window must take effect within a few seconds.
5. Status screens during night (offline screen, "Firmware update") stay at night brightness; after an OTA reboot at night the display is bright only until the first server answer.

---

### Task 1: Server sends `X-Local-Time`

**Files:**
- Modify: `server/glancebox/app.py` (`create_app`, `jpeg_response`)
- Test: `server/tests/test_app.py`

**Interfaces:**
- Produces: header `X-Local-Time` with value `HH:MM:SS` (zero-padded, 24 h, `cfg.timezone`, computed from `clock()`) on every `/api/v1/frame` response: 200, 304 and error frame.

- [ ] **Step 1: Write the failing tests**

```python
def test_frame_has_local_time_header():
    # NOW = 1_000_000.0 → 1970-01-12 13:46:40 UTC → 14:46:40 Europe/Berlin (CET)
    client, _ = make_client(filled_store())
    r = client.get("/api/v1/frame")
    assert r.headers["x-local-time"] == "14:46:40"

def test_local_time_on_304_and_error_frame():
    client, _ = make_client(filled_store())
    etag = client.get("/api/v1/frame").headers["etag"]
    assert client.get("/api/v1/frame", headers={"If-None-Match": etag}).headers["x-local-time"] == "14:46:40"
    empty_client, _ = make_client()            # no frames → error frame path
    assert empty_client.get("/api/v1/frame").headers["x-local-time"] == "14:46:40"

def test_local_time_respects_dst():
    # 2026-07-01 00:30:00 UTC → 02:30:00 CEST
    client, _ = make_client(filled_store_at(1782865800.0), now=1782865800.0)
    assert client.get("/api/v1/frame").headers["x-local-time"] == "02:30:00"
```

(`filled_store_at(t)` = `filled_store()` with timestamps relative to `t`; add it next to `filled_store`. If `make_client()` without a store does not reach the error-frame path, use the existing setup of `test_frame_all_pages_down_returns_error_frame`.)

- [ ] **Step 2: Run** `cd server && .venv/bin/pytest tests/test_app.py -q` → the three tests FAIL (KeyError `x-local-time`).
- [ ] **Step 3: Implement.** Build `ZoneInfo(cfg.timezone)` once in `create_app`; in `jpeg_response` add `"X-Local-Time": datetime.fromtimestamp(clock(), tz).strftime("%H:%M:%S")`.
- [ ] **Step 4: Run** the full server suite `cd server && .venv/bin/pytest -q` → all PASS.
- [ ] **Step 5: Commit** `feat(server): send local time with every frame`.

---

### Task 2: Core night logic and settings fields

**Files:**
- Create: `firmware/lib/core/night.h`, `firmware/lib/core/night.cpp`
- Modify: `firmware/lib/core/settings.h`, `firmware/lib/core/settings.cpp`
- Test: `firmware/test/test_core/test_main.cpp`

**Interfaces:**
- Produces (namespace `gb`):
  - `int32_t parseLocalTime(const char* s);` → seconds of day 0–86399 for exactly `HH:MM:SS` (00–23, 00–59, 00–59), else -1 (also for nullptr).
  - `int parseHhMm(const char* s);` → minutes 0–1439 for exactly `HH:MM`, else -1.
  - `std::string formatHhMm(uint16_t minutes);` → `"07:05"`.
  - `class LocalClock { public: void sync(uint32_t secOfDay, uint32_t nowMs); bool known() const; uint32_t secondOfDay(uint32_t nowMs) const; };` (uses `nowMs - syncMs` unsigned, result modulo 86400).
  - `bool nightActive(uint16_t start, uint16_t end, uint16_t minuteOfDay);`
  - `uint8_t effectiveBrightness(const Settings& s, bool timeKnown, uint32_t secondOfDay);` → `s.nightBrightness` when time known and night active, else `s.brightness`.
  - `Settings` gains `uint16_t nightStart = 0; uint16_t nightEnd = 0; uint8_t nightBrightness = 0;`
  - `uint8_t clampNightBrightness(int pct);` → 0–100.
  - `bool applyNight(Settings& s, const std::string& start, const std::string& end, const std::string& brightness, std::string* error);` errors `"bad_time"`, `"bad_night_brightness"`; s unchanged on failure.
  - `encodeSettings` writes `night_start`, `night_end`, `night_brightness`; `parseSettings` reads them (out-of-range minutes → keep default 0; brightness clamped).

- [ ] **Step 1: Write the failing tests** (add `RUN_TEST` lines):

```cpp
void test_parse_local_time() {
  TEST_ASSERT_EQUAL_INT32(0, gb::parseLocalTime("00:00:00"));
  TEST_ASSERT_EQUAL_INT32(86399, gb::parseLocalTime("23:59:59"));
  TEST_ASSERT_EQUAL_INT32(-1, gb::parseLocalTime("24:00:00"));
  TEST_ASSERT_EQUAL_INT32(-1, gb::parseLocalTime("12:60:00"));
  TEST_ASSERT_EQUAL_INT32(-1, gb::parseLocalTime("1:00:00"));
  TEST_ASSERT_EQUAL_INT32(-1, gb::parseLocalTime("12:00:00 "));
  TEST_ASSERT_EQUAL_INT32(-1, gb::parseLocalTime(""));
  TEST_ASSERT_EQUAL_INT32(-1, gb::parseLocalTime(nullptr));
}
void test_parse_format_hhmm() {
  TEST_ASSERT_EQUAL_INT(1320, gb::parseHhMm("22:00"));
  TEST_ASSERT_EQUAL_INT(-1, gb::parseHhMm("22:00:00"));
  TEST_ASSERT_EQUAL_INT(-1, gb::parseHhMm("7:00"));
  TEST_ASSERT_EQUAL_STRING("07:05", gb::formatHhMm(425).c_str());
}
void test_night_window() {
  TEST_ASSERT_FALSE(gb::nightActive(0, 0, 0));          // start == end: off
  TEST_ASSERT_TRUE(gb::nightActive(1320, 420, 1439));   // 23:59
  TEST_ASSERT_TRUE(gb::nightActive(1320, 420, 0));      // 00:00
  TEST_ASSERT_TRUE(gb::nightActive(1320, 420, 419));    // 06:59
  TEST_ASSERT_FALSE(gb::nightActive(1320, 420, 420));   // 07:00
  TEST_ASSERT_FALSE(gb::nightActive(1320, 420, 1319));  // 21:59
  TEST_ASSERT_TRUE(gb::nightActive(1320, 420, 1320));   // 22:00
  TEST_ASSERT_TRUE(gb::nightActive(60, 120, 60));       // same-day window
  TEST_ASSERT_FALSE(gb::nightActive(60, 120, 120));
}
void test_local_clock() {
  gb::LocalClock c;
  TEST_ASSERT_FALSE(c.known());
  c.sync(86390, 1000);                                   // 23:59:50
  TEST_ASSERT_TRUE(c.known());
  TEST_ASSERT_EQUAL_UINT32(86395, c.secondOfDay(6000));
  TEST_ASSERT_EQUAL_UINT32(10, c.secondOfDay(21000));    // wraps past midnight
  gb::LocalClock w;
  w.sync(0, 0xFFFFF000u);                                // millis() about to overflow
  TEST_ASSERT_EQUAL_UINT32(10, w.secondOfDay(0xFFFFF000u + 10000u));
}
void test_effective_brightness() {
  gb::Settings s; s.brightness = 80; s.nightStart = 1320; s.nightEnd = 420; s.nightBrightness = 0;
  TEST_ASSERT_EQUAL_UINT8(80, gb::effectiveBrightness(s, false, 23 * 3600));  // time unknown
  TEST_ASSERT_EQUAL_UINT8(0, gb::effectiveBrightness(s, true, 23 * 3600));
  TEST_ASSERT_EQUAL_UINT8(80, gb::effectiveBrightness(s, true, 12 * 3600));
}
void test_apply_night() {
  gb::Settings s; std::string err;
  TEST_ASSERT_TRUE(gb::applyNight(s, "22:00", "07:00", "10", &err));
  TEST_ASSERT_EQUAL_UINT16(1320, s.nightStart);
  TEST_ASSERT_EQUAL_UINT8(10, s.nightBrightness);
  TEST_ASSERT_FALSE(gb::applyNight(s, "25:00", "07:00", "10", &err));
  TEST_ASSERT_EQUAL_STRING("bad_time", err.c_str());
  TEST_ASSERT_FALSE(gb::applyNight(s, "22:00", "07:00", "101", &err));
  TEST_ASSERT_EQUAL_STRING("bad_night_brightness", err.c_str());
  TEST_ASSERT_EQUAL_UINT16(1320, s.nightStart);            // unchanged on failure
}
void test_settings_night_roundtrip_and_old_file() {
  gb::Settings s; s.nightStart = 1320; s.nightEnd = 420; s.nightBrightness = 5;
  gb::Settings back;
  TEST_ASSERT_TRUE(gb::parseSettings(gb::encodeSettings(s), &back));
  TEST_ASSERT_EQUAL_UINT16(1320, back.nightStart);
  TEST_ASSERT_EQUAL_UINT16(420, back.nightEnd);
  TEST_ASSERT_EQUAL_UINT8(5, back.nightBrightness);
  gb::Settings old;   // 0.1.0 file without night keys
  TEST_ASSERT_TRUE(gb::parseSettings(
      "{\"server_url\":\"http://h:8090\",\"update_password\":\"abcdefgh\",\"brightness\":70}\n", &old));
  TEST_ASSERT_EQUAL_UINT8(70, old.brightness);
  TEST_ASSERT_EQUAL_UINT16(0, old.nightStart);
  TEST_ASSERT_EQUAL_UINT16(0, old.nightEnd);
}
```

- [ ] **Step 2: Run** `cd firmware && pio test -e native` → build FAILS (missing `night.h` / fields).
- [ ] **Step 3: Implement** `night.h/.cpp` and the settings changes per the Interfaces block. `parseSettings`: `night_start`/`night_end` outside 0–1439 → keep 0; `night_brightness` via `clampNightBrightness`.
- [ ] **Step 4: Run** `cd firmware && pio test -e native` → all PASS (previous 53 + new).
- [ ] **Step 5: Commit** `feat(firmware): night window, local clock and night settings in core`.

---

### Task 3: Firmware wiring (clock sync, backlight, web page, status)

**Files:**
- Modify: `firmware/src/frame_client.h/.cpp` (collect `X-Local-Time`, new field `int32_t localSec` = `gb::parseLocalTime(...)`, -1 if absent/invalid; read the header via `strOrEmpty` from `src/arduino_str.h`)
- Modify: `firmware/src/display.h/.cpp` (`void displaySetBacklight(uint8_t pct);` 0–100, 0 = backlight fully off; `displaySetBrightness` stays for day values)
- Modify: `firmware/src/main.cpp` (global `gb::LocalClock localClock`; in `pollFrame` call `localClock.sync(r.localSec, millis())` when `r.status > 0 && r.localSec >= 0`; in `loop` at most once per second compute `gb::effectiveBrightness(settings, localClock.known(), localClock.secondOfDay(now))` and call `displaySetBacklight` only when it differs from the last applied value)
- Modify: `firmware/src/web_ui.h/.cpp` (`StatusProvider` gains `int32_t (*localMinute)()` (-1 unknown) and `bool (*night)()`; `/status` JSON gains `"local_time":"HH:MM"|null` and `"night":true|false`; status table rows for both; settings form gains `night_start`/`night_end` (`type=time`, value `formatHhMm`) and `night_brightness` (`type=number min=0 max=100`) plus the hint; `handleSettings` validates with `gb::applyNight` and returns 400 with the matching message; in normal mode `handleSettings` no longer calls `displaySetBrightness` (the main loop applies within 1 s); in safe mode it still does)
- Modify: `firmware/src/i18n.h/.cpp` (new `Msg` entries DE/EN: NightStart „Nacht von“/"Night from", NightEnd „Nacht bis“/"Night until", NightBrightness „Helligkeit nachts (%)“/"Night brightness (%)", NightHint „Gleiche Zeiten = Nachtmodus aus. 0 % = ganz dunkel.“/"Same times = night mode off. 0 % = completely dark.", LocalTime „Uhrzeit“/"Local time", Night „Nacht“/"Night", ErrNightTime „Zeit im Format HH:MM“/"Time must be HH:MM", ErrNightBrightness „Helligkeit nachts muss 0 bis 100 sein“/"Night brightness must be 0 to 100")
- Modify: `firmware/src/safe_mode.cpp` (StatusProvider: `localMinute` → -1, `night` → false)

**Interfaces:**
- Consumes: Task 2 (`gb::LocalClock`, `gb::effectiveBrightness`, `gb::nightActive`, `gb::applyNight`, `gb::formatHhMm`, `gb::parseLocalTime`).

- [ ] **Step 1: Build** `.superpowers/sdd/2026-11-14-glancebox/pio-docker.sh run -e ultra -e ultra-crashtest -e spike` → SUCCESS; `python3 tools/check_fw_size.py firmware/.pio/build/ultra/firmware.bin firmware/size-limit.txt` → OK.
- [ ] **Step 2: Native tests still green:** `cd firmware && pio test -e native` → all PASS.
- [ ] **Step 3: Commit** `feat(firmware): night mode on the device page`.

(Behaviour of this task is verified on the device in Task 5; the logic it calls is covered by Task 2.)

---

### Task 4: Docs, changelog, version

**Files:**
- Modify: `docs/de/setup.md`, `docs/en/setup.md` (new section „Nachtmodus“ / "Night mode" after „Die Geräteseite“ / "The device web page": what the three fields do, 22:00–07:00 example, same times = off, 0 % = dark, time comes from the server's `timezone`, a device that starts at night without a server stays bright until the server answers, safe mode ignores night mode)
- Modify: `CHANGELOG.md` (`## [Unreleased]` → `### Added` night mode line; server line about `X-Local-Time`)
- Modify: `VERSION` → `0.2.0`; in `CHANGELOG.md` rename the Unreleased content to `## [0.2.0]` and keep an empty `## [Unreleased]` above it

- [ ] **Step 1:** Write both sections; run `python3 tools/check_docs_parity.py` → `OK`.
- [ ] **Step 2:** `cd server && .venv/bin/pytest tests/test_changelog_section.py tests/test_docs_parity.py -q` → PASS; `python3 tools/changelog_section.py 0.2.0` prints the new section.
- [ ] **Step 3: Commit** `docs: night mode; version 0.2.0`.

---

### Task 5: Device verification (needs Robin's device and update password)

- [ ] **Step 1:** Deploy server branch on the homeserver (`~/zugtafel`: `git fetch && git switch nachtmodus && docker compose up -d --build`); `curl -sI http://<server-ip>:8090/api/v1/frame | grep -i x-local-time` matches the wall clock.
- [ ] **Step 2:** OTA the new `ultra` image; `/status` shows `local_time` within a minute of the real time, `night:false`.
- [ ] **Step 3:** Set the window to [now−1 min, now+3 min], night brightness 0 → display goes dark within a few seconds, `/status` `night:true`; after the end time it lights up again.
- [ ] **Step 4:** Window across now with night brightness 0, then stop the server (`docker compose stop`) → stays dark; offline screen appears dark; start server.
- [ ] **Step 5:** During night window, OTA the same image → after reboot bright only until the first frame answer, then dark again.
- [ ] **Step 6:** Rerun `tools/ota-smoketest.sh` (new 0.2.0 vs 0.1.0 release bin) → `PASS`. Record results in the ledger.
