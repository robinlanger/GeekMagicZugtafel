# Neue Web-Oberfläche – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the device web page with an Apple-style UI (Home-app tiles + iOS grouped lists, live brightness sliders, auto-save) served from embedded, gzipped CSS/JS.

**Architecture:** Firmware still renders the HTML (i18n, values, safe mode) in `web_ui.cpp`. `firmware/web/app.css` + `app.js` are minified and gzipped at build time by a PlatformIO pre-script into a generated PROGMEM header and served cached. Two new JSON endpoints (`/api/brightness-preview`, `/api/settings`) back the live controls; their decision logic lives in `lib/core` with native tests.

**Tech Stack:** ESP8266 Arduino (ESP8266WebServer), PlatformIO, Unity native tests, Python 3.12 (build script + pytest), vanilla JS/CSS (no libraries, no network).

**Spec:** `docs/superpowers/specs/2026-11-18-web-oberflaeche-design.md`

**Branch:** `fix/backlight-curve` (already has the backlight fix `08b5aa6` and the spec `bf18c21`).

## Global Constraints

- Nothing loaded from the internet; system font stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
- CSS + JS together ≤ 8 KB gzip; main page HTML ≤ 6 KB.
- Every state-changing route goes through `webUiAuthorize()` (Origin + Basic Auth `admin`).
- Preview never writes flash; preview hold time **3000 ms** after the last preview request.
- Flash layout unchanged; firmware must pass `tools/check_fw_size.py` with `firmware/size-limit.txt`.
- All user-visible text DE + EN via `i18n`; JS contains no translations (gets them from the page).
- WLAN words: RSSI ≥ −60 „Sehr gut“/"Excellent", ≥ −70 „Gut“/"Good", ≥ −80 „Mäßig“/"Fair", else „Schwach“/"Weak".
- Breakpoint ~720 px: below one column / 2×2 tiles; above 4 tiles in a row and two list columns; content max ~900 px.
- Safe mode page: new CSS only, no JS, behaviour unchanged.
- `POST /settings` (old form) stays; `<noscript>` form with „Sichern“ for no-JS clients.
- `env:native` builds/tests must not depend on the generated header.

## Review Focus

1. Slider dragged quickly: preview requests overlap on a single-threaded server → JS must keep at most one request in flight and send only the latest value (test: manual on device; JS logic reviewed).
2. Releasing the slider while a preview is in flight: the save must still win and the display must end at the saved value, not snap back after 3 s (core test `test_preview_expires_and_saved_value_applies`).
3. `millis()` wraparound during an active preview (core test `test_preview_millis_wraparound`).
4. Patch with one invalid field among valid ones: nothing is saved, error names the field (core test `test_settings_patch_atomic_on_error`).
5. First write without credentials: browser shows Basic-Auth prompt for `fetch` 401 and the retried request succeeds; a cancelled prompt shows an error, not a stuck ✓ (manual check on device).

---

### Task 1: Core logic – brightness preview window

**Files:**
- Modify: `firmware/lib/core/night.h`, `firmware/lib/core/night.cpp`
- Test: `firmware/test/test_core/test_main.cpp`

**Interfaces:**
- Produces:
  ```cpp
  constexpr uint32_t kPreviewHoldMs = 3000;
  class BacklightPreview {
   public:
    void set(uint8_t pct, uint32_t nowMs);   // pct clamped to 0..100
    void clear();
    bool active(uint32_t nowMs) const;       // true while nowMs - lastSetMs < kPreviewHoldMs
    uint8_t pct() const;
  };
  ```

- [ ] **Step 1: Write failing tests** `test_preview_inactive_by_default`, `test_preview_holds_3s_then_expires` (set(40, 1000): active at 3999, inactive at 4000), `test_preview_refresh_extends` (set at 0 and 2500 → active at 5499), `test_preview_millis_wraparound` (set at 0xFFFFF000 → active at 0x00000100, inactive at 0xFFFFF000+3000), `test_preview_expires_and_saved_value_applies` (set then clear() → inactive immediately), `test_preview_clamps` (set(250) → pct()==100). Register with RUN_TEST.
- [ ] **Step 2:** `pio test -e native` → compile error (undeclared `BacklightPreview`).
- [ ] **Step 3:** Implement in `night.h/.cpp` (unsigned subtraction for the window).
- [ ] **Step 4:** `pio test -e native` → all PASS.
- [ ] **Step 5:** Commit `feat(core): brightness preview window`.

### Task 2: Core logic – partial settings patch and status formatting

**Files:**
- Modify: `firmware/lib/core/settings.h`, `firmware/lib/core/settings.cpp`, `firmware/lib/core/web_util.h`, `firmware/lib/core/web_util.cpp`
- Test: `firmware/test/test_core/test_main.cpp`

**Interfaces:**
- Consumes: `applyServerUrl`, `applyPassword`, `applyNight`, `parseHhMm` (existing).
- Produces:
  ```cpp
  // settings.h
  struct SettingsPatch {  // absent field = leave unchanged
    std::optional<std::string> serverUrl, password, brightness,
                               nightStart, nightEnd, nightBrightness;
  };
  // Applies all present fields to a copy; on any error s is unchanged, *field is the form
  // name ("server_url", "password", "brightness", "night_start", "night_end",
  // "night_brightness") and *error the existing code ("https_unsupported", "too_short",
  // "bad_brightness", "bad_time", "bad_night_brightness", ...). Returns true on success.
  bool applySettingsPatch(Settings& s, const SettingsPatch& p, std::string* field, std::string* error);
  // web_util.h
  enum class WifiQuality : uint8_t { Excellent, Good, Fair, Weak };
  WifiQuality wifiQuality(int rssiDbm);
  ```
- Brightness string rule: decimal digits only, 5..100, else `"bad_brightness"`. Night start/end: only one of them present → combine with the current value of the other (use `formatHhMm` + `applyNight`).

- [ ] **Step 1: Write failing tests**
  - `test_settings_patch_single_field`: patch `{brightness:"30"}` → true, brightness 30, other fields unchanged.
  - `test_settings_patch_night_start_only`: current 22:00–07:00, patch `{nightStart:"21:30"}` → 1290/420.
  - `test_settings_patch_night_off`: patch start="00:00", end="00:00" → both 0.
  - `test_settings_patch_atomic_on_error`: patch `{brightness:"40", serverUrl:"https://x"}` → false, field `"server_url"`, error `"https_unsupported"`, brightness still old.
  - `test_settings_patch_bad_brightness`: `"4"`, `"101"`, `"5a"`, `""` → false, field `"brightness"`, error `"bad_brightness"`.
  - `test_settings_patch_password`: `"short"` → field `"password"`, `"too_short"`; `"longenough1"` → stored.
  - `test_settings_patch_empty`: no fields → true, unchanged.
  - `test_wifi_quality`: −50→Excellent, −60→Excellent, −61→Good, −70→Good, −71→Fair, −80→Fair, −81→Weak.
- [ ] **Step 2:** `pio test -e native` → compile errors.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** `pio test -e native` → all PASS.
- [ ] **Step 5:** Commit `feat(core): partial settings patch and wifi quality`.

### Task 3: Build pipeline – embed gzipped web assets

**Files:**
- Create: `tools/webasset.py` (pure functions), `firmware/scripts/embed_web.py` (PlatformIO pre-script), `firmware/web/app.css`, `firmware/web/app.js` (minimal placeholders now: one rule / one comment+statement), `server/tests/test_webasset.py`
- Modify: `firmware/platformio.ini` (`extra_scripts` of `env:ultra`: add `pre:scripts/embed_web.py`), `firmware/src/web_ui.cpp` (serve routes), `.gitignore` if the output dir is not under `.pio`

**Interfaces:**
- Produces (Python, `tools/webasset.py`):
  - `minify_css(src: str) -> str`: drop `/* */` comments, collapse whitespace, remove spaces around `{}:;,>` – never inside quoted strings or `url(...)`.
  - `minify_js(src: str) -> str`: conservative: drop full-line `//` comments and `/* */` blocks outside strings/template literals, strip leading/trailing whitespace per line, drop blank lines (keep newlines → no ASI breakage).
  - `gzip_bytes(data: bytes) -> bytes`: `gzip.compress(data, 9, mtime=0)` (reproducible).
  - `render_header(assets: dict[str, bytes]) -> str`: for each name (`app_css`, `app_js`) emits `const uint8_t kWeb_<name>[] PROGMEM = {...}; constexpr size_t kWeb_<name>Len = N;` and `constexpr char kWebHash[] = "<first 8 hex of sha256 over all gz>";`.
- Produces (C++): generated header `web_assets.h` in `$BUILD_DIR/generated/` (added to `CPPPATH` by the pre-script), routes `GET /app.css`, `GET /app.js` registered in `beginCommon` (both modes): `Content-Encoding: gzip`, `Cache-Control: public, max-age=31536000, immutable`, `send_P`.

- [ ] **Step 1: Write failing pytest** `server/tests/test_webasset.py` (import via path like `test_check_fw_size.py`): `test_minify_css_keeps_strings_and_urls` (`a{content:"a  b"}` keeps two spaces; `url( x.png )` unchanged inside parens), `test_minify_css_removes_comments_and_space`, `test_minify_js_keeps_strings_with_slashes` (`"http://x"` and `'// no'` kept), `test_minify_js_drops_comment_lines`, `test_gzip_reproducible_and_roundtrip`, `test_render_header_lengths_and_hash` (lengths match, hash 8 hex chars, stable).
- [ ] **Step 2:** `cd server && pytest -q tests/test_webasset.py` → FAIL (module missing).
- [ ] **Step 3:** Implement `tools/webasset.py`, then `embed_web.py` (reads `firmware/web/*`, writes header only when content changed), routes in `web_ui.cpp`.
- [ ] **Step 4:** `pytest -q tests/test_webasset.py` PASS; `pio test -e native` PASS (native untouched).
- [ ] **Step 5:** Commit `build(firmware): embed gzipped web assets`.

### Task 4: Strings and HTML rendering (normal page, messages, safe page) + CSS

**Files:**
- Modify: `firmware/src/i18n.h`, `firmware/src/i18n.cpp`, `firmware/src/web_ui.cpp`, `firmware/web/app.css`
- Optionally create: `firmware/src/web_pages.cpp/.h` if `web_ui.cpp` grows past ~600 lines (HTML rendering only; routes/OTA stay in `web_ui.cpp`).

**Interfaces:**
- Consumes: `kWebHash`, `wifiQuality`, existing status provider.
- Produces (DOM contract for Task 6, exact ids/attributes):
  - `<body data-i18n='{...}'>` JSON with keys: `online, offline, ago_s, ago_m, ago_h, day_short, hour_short, min_short, wifi_excellent, wifi_good, wifi_fair, wifi_weak, off, saved, undo, error_generic, auth_cancelled, pw_changed, upload_progress, upload_ok, reset_confirm`.
  - Tiles: `#t-conn`, `#t-age`, `#t-wifi`, `#t-up` (values rendered server-side too).
  - Controls: `<input type=range id=brightness name=brightness min=5 max=100>`, `<input type=checkbox id=night_on role=switch>`, `<input type=time id=night_start>`, `<input type=time id=night_end>`, `<input type=range id=night_brightness min=0 max=100>`, `<input id=server_url>`, password form `#pw-form` (`<input type=password name=password>` + button), update form `#update-form` (md5 + file + `<progress id=up-progress hidden>`), restart/reset forms as today.
  - Each saving control is wrapped in an element with class `row` that can receive `data-state="saving|ok|error"` and contains a `.msg` span.
  - `<noscript>`: the old full form posting to `/settings` with a Save button; the JS-driven controls carry `class=js-only` (hidden by CSS until `<html class=js>`).
  - Page head references `/app.css?v=<kWebHash>` and (normal page only) `<script defer src=/app.js?v=<kWebHash>>`.
- New i18n Msg values (DE/EN) for: group titles (Display, Server, Device, Details), Night mode, From, To, Change password, Change, Off, Online/Offline, Excellent/Good/Fair/Weak, „Läuft seit“/"Up for", `ErrBrightnessRange` reuse existing `ErrBrightness`, Undo, Saved ✓ text, Auth-cancelled text, upload texts.

- [ ] **Step 1:** Add Msg entries + DE/EN strings (keep `kEn`/`kDe` arrays and static_asserts in sync).
- [ ] **Step 2:** Rewrite `kHead`/`sendPage` (head with viewport, `color-scheme`, CSS link), `handleRoot` (tiles, groups, details, noscript form), `sendMessage` (card look), `handleSafePage` (same CSS, groups, plain update form, no script).
- [ ] **Step 3:** Write `app.css` from the mockups `mix.html`/`desktop.html` (light + `prefers-color-scheme: dark` gradient/glass, range styled as Control-Center bar, iOS switch, red destructive rows, focus ring, `prefers-reduced-motion`).
- [ ] **Step 4: Verify without hardware:** `pio test -e native` PASS. Copy the markup `handleRoot` emits (with sample values) into `.superpowers/dev.html` (not committed) linking `firmware/web/app.css`, and check it in a browser at 375 px and 1200 px, light + dark. The real page is checked on the device in Task 7.
- [ ] **Step 5:** Commit `feat(firmware): apple-style device page markup and styles`.

### Task 5: JSON endpoints

**Files:**
- Modify: `firmware/src/web_ui.cpp`, `firmware/src/web_ui.h`, `firmware/src/main.cpp`

**Interfaces:**
- Consumes: `BacklightPreview`, `applySettingsPatch`, `settingsSave`, `msgForError`, `tr`.
- Produces:
  - `StatusProvider` gains `void (*previewBrightness)(uint8_t pct) = nullptr;` and `void (*settingsChanged)() = nullptr;`.
  - `POST /api/brightness-preview` (form field `pct`, 0..100 digits): authorize → call `previewBrightness` → `{"ok":true}`; bad value → 400 `{"ok":false,"error":"…"}`.
  - `POST /api/settings` (form fields, any subset of `server_url, password, brightness, night_start, night_end, night_brightness`): authorize → `applySettingsPatch` on a copy → `settingsSave` → `*settings = next` → `settingsChanged()` → `{"ok":true}`; validation error → 400 `{"ok":false,"field":"<name>","error":"<tr text, JSON-escaped>"}`; save failure → 500 with `ErrSaveFailed`.
  - Only in `webUiBegin` (normal mode).
  - `main.cpp`: global `gb::BacklightPreview preview`; `previewBrightness` → `preview.set(pct, millis())`; `settingsChanged` → `preview.clear(); lastBacklight = -1;` (forces re-apply next loop); `updateBacklight`: when `preview.active(now)` use `preview.pct()` and skip the 1 s throttle; otherwise effective brightness as today.
- Map patch error codes to messages: `bad_brightness`→`ErrBrightness`, `bad_time`→`ErrNightTime`, `bad_night_brightness`→`ErrNightBrightness`, rest via `msgForError(code, field=="password")`.

- [ ] **Step 1:** Implement routes + main wiring (logic already tested in Tasks 1–2; this task is glue).
- [ ] **Step 2:** `pio test -e native` PASS; compile check happens in Task 7 (no local ESP toolchain).
- [ ] **Step 3:** Commit `feat(firmware): live preview and partial settings endpoints`.

### Task 6: app.js – live controls

**Files:**
- Modify: `firmware/web/app.js`
- Create (dev only, not embedded, not committed): `.superpowers/md5-check.mjs` to compare the JS MD5 with `node:crypto` on a few buffers incl. 0, 55, 56, 64, 1 MiB bytes.

**Interfaces:**
- Consumes: DOM contract from Task 4, endpoints from Task 5, `/status` JSON (existing keys `rssi`, `last_frame_age_s`, `uptime_s`, `frames_ok`, `night`, `local_time`).
- Behaviour (spec „Verhalten sofort übernehmen“):
  - On load: `document.documentElement.classList.add('js')`.
  - `post(url, fields)`: `fetch(url, {method:'POST', body:new URLSearchParams(fields), credentials:'same-origin'})`; parse JSON; non-OK → throw with server `error`/`field`. 401 without prompt → show `auth_cancelled`.
  - Sliders: `input` → update label, preview with **one request in flight, latest value queued**; `change` (release) → wait for in-flight preview, then `POST /api/settings` with that field; row state saving→ok (✓ 1.5 s) or error (revert slider to last saved value, show message). Night slider label shows `off` at 0.
  - Night switch: off → save `night_start=night_end=<current start>`; on → save remembered times (from the page) or `22:00`/`07:00`; time rows hidden when off.
  - Time fields + server URL: save on `change`/Enter when value differs from last saved; server URL success shows `undo` link for 8 s that re-saves the previous value.
  - Password form: submit → `POST /api/settings` `password=…` → show `pw_changed`.
  - Update form: on file pick compute MD5 (own compact implementation over `ArrayBuffer`) into the md5 field; submit via `XMLHttpRequest` with `upload.onprogress` → `<progress>`; on 200 show `upload_ok` and reload after 15 s.
  - Reset form keeps `confirm(i18n.reset_confirm)`.
  - Status refresh every 5 s from `/status` → tiles (age/uptime formatting with i18n units, wifi words with thresholds from Global Constraints).

- [ ] **Step 1:** Write `md5-check.mjs`, run with the md5 function extracted → mismatch/undefined first.
- [ ] **Step 2:** Implement `app.js`; `node .superpowers/md5-check.mjs` → all match.
- [ ] **Step 3:** `cd server && pytest -q tests/test_webasset.py`; check gz budget: `python3 -c` using `tools/webasset.py` → css+js gz ≤ 8192.
- [ ] **Step 4:** Commit `feat(firmware): live controls in the device page`.

### Task 7: Docs, build, size, deploy

**Files:**
- Modify: `CHANGELOG.md` (Unreleased: Added new device page, live brightness, auto-save, md5 in browser; Changed: safe-mode look), `docs/en/setup.md`, `docs/de/setup.md` (section „The device web page“: new layout, auto-save, password button; same headings both sides)

- [ ] **Step 1:** Docs + changelog; `python3 tools/check_docs_parity.py` → exit 0.
- [ ] **Step 2: Build on the home server** (no ESP toolchain on the Mac): `git archive HEAD | ssh server 'rm -rf ~/gb-build && mkdir ~/gb-build && tar -x -C ~/gb-build'`, set `VERSION` in that copy to `0.5.0-dev`, then `docker run --rm -v ~/gb-build:/w -w /w/firmware python:3.12 sh -c 'pip install -q platformio==6.2.0 && pio test -e native && pio run -e ultra && python3 ../tools/check_fw_size.py .pio/build/ultra/firmware.bin size-limit.txt'` → SUCCESS, size OK. Copy `firmware.bin` back.
- [ ] **Step 3: OTA to <device-ip>** (user approved 2026-11-18): `curl -u admin:<pw> -F md5=<md5> -F firmware=@firmware.bin http://<device-ip>/update` (password requested via secret prompt) → `update ok`; `/status` shows `0.5.0-dev`, `boot_failed` 0.
- [ ] **Step 4: Device checks:** page light/dark at phone + desktop width; brightness 5 vs 100 clearly different; live slider; save + reload keeps values; night switch; wrong server URL rejected (`https://`), undo works; `/status` `heap_free` not markedly below ~37 KB.
- [ ] **Step 5:** Commit docs; clean up `~/gb-build` on the server.
