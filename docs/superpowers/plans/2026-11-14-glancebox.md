# Glance Box Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `zugtafel` repo into `glancebox`. It has two parts: open firmware that makes a GeekMagic SmallTV Ultra (ESP8266) fetch pre-rendered JPEG frames over HTTP and draw them from RAM, and a Docker server that renders a YAML playlist of 240×240 web pages with headless Chromium.

**Architecture:** The server (Python, FastAPI, Playwright) pre-renders every playlist page in the background into a frame cache. It serves `GET /api/v1/frame` and picks the current page statelessly from wall-clock time. The firmware (PlatformIO, Arduino) polls that endpoint, buffers the JPEG (≤ 24 KB) and decodes it MCU-block-wise onto the ST7789. A boot guard in RTC memory drops into a minimal safe mode (Wi-Fi + update page) after 3 failed boots. Pure firmware logic lives in a hardware-free library that runs under `pio test -e native`.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Playwright (Chromium), Jinja2, PyYAML, Pillow, requests, pytest, ruff · PlatformIO `espressif8266`, Arduino, TFT_eSPI, TJpg_Decoder, WiFiManager, Unity · GitHub Actions, GHCR.

**Spec:** `docs/superpowers/specs/2026-11-14-glancebox-design.md`. Read it before any task. Section numbers below refer to it.

## Global Constraints

- Code, comments, identifiers and commit messages: **English**. User-facing docs: EN and DE with the same structure.
- One version for firmware and server, in the repo-root file `VERSION` (start `0.1.0`). Firmware gets it as `-DGB_VERSION="..."`, and the server reads the same file.
- All dependencies are pinned exactly: `platformio.ini` (platform + libs `@x.y.z`), `server/requirements.lock`, Docker base images by tag. Pin the newest stable versions available at implementation time, and record them.
- Hardware (verify in Task 11 / H2): ESP-12F, board `esp12e`. ST7789V 240×240, SPI mode 3, 40 MHz, **no CS**. CLK GPIO14, MOSI GPIO13, DC GPIO0, RST GPIO2. Backlight GPIO5 PWM **inverted**. BGR, display inversion on.
- Protocol: `GET /api/v1/frame?id=<chip-id>&fw=<version>` with optional `If-None-Match`. Responses `200 image/jpeg` + `ETag` + `X-Next-In`, or `304` + `X-Next-In`. `X-Next-In` is always clamped to **2–30 s**.
- JPEG: baseline (not progressive), 240×240, quality 85, stepping down to a minimum of 40 until it is **≤ 24 576 bytes** (`MAX_JPEG_BYTES`, same constant on both sides).
- Playlist: default `interval: 30` s per page. Per-page `duration` and `refresh`. `bahn` refresh is **at least 60 s** (DBF rule).
- A failed page keeps its last good frame for at most **600 s**, then it is skipped. If no page is available, serve an error frame, never black.
- Boot guard: increment the counter as the **first** thing in `setup()`. Healthy = **60 s uptime AND Wi-Fi connected AND web server running**; the counter then resets to 0. **3 failed boots → safe mode.**
- Device shows an offline status screen after **120 s** without a successful frame.
- Device writes flash only when saving settings and during OTA.
- OTA: `POST /update` behind HTTP Basic auth (user `admin`, password set in portal, min 8 chars). **MD5 required**; reject on mismatch and keep running the old image.
- AP name `GlanceBox-XXXX` (last 4 hex digits of chip ID). The device web UI is DE/EN by `Accept-Language`.
- Server: no auth (LAN). Port 8080. Runs as non-root. Multi-arch image (amd64, arm64).
- License MIT. DejaVu fonts with their license move along.

## Review Focus

1. **Bad `config.yaml`** (unknown page type, missing `station`, `refresh: 10` on `bahn`, YAML syntax error). Expect a startup error that names the page as `pages[<i>]`, not a traceback deep in a render. Owner: Tasks 2 and 3 (`test_unknown_type_names_index`, `test_bahn_refresh_below_60_rejected`).
2. **A `url` page that hangs or never finishes loading.** Expect the render to time out after `timeout_s` and the page to count as failed, while `/api/v1/frame` keeps answering from cache. Owner: Task 5 (`test_render_url_timeout_raises`) and Task 6 (`test_failing_page_does_not_block_others`).
3. **Every page failing** (DBF down and homelab URL down). Expect the error frame, not a 500 or black screen. Owner: Task 7 (`test_frame_all_pages_down_returns_error_frame`).
4. **Device sends an ETag from before a server restart.** Expect `200` with a fresh frame, never a `304` that pins an old image. Owner: Task 7 (`test_stale_etag_after_restart_gets_200`).
5. **Server URL typed in the portal as `homeserver:8080/`, with spaces or as `https://…`.** Expect it normalized to `http://homeserver:8080`, or rejected with a clear message for https (no TLS on ESP8266). Owner: Task 10 (`test_normalize_server_url_*`).

---

## Hardware hold points (owner, real device)

The tasks below are interleaved with these. The executor **stops** at each one and waits for the owner.

- **H1 – Backup (hard stop before ANY flashing).**
  1. Owner flashes `debugprobe` onto the Pico.
  2. Owner wires GND, Pico GP4(TX)→ESP RX, Pico GP5(RX)→ESP TX, and holds GPIO0 to GND at power-up. The Ultra is powered via its own USB-C.
  3. Owner runs `esptool.py --port <pico-port> --baud 115200 read_flash 0 ALL stock-backup.bin` twice and checks that both SHA-256 values match. Stores the backup outside the repo.
  4. Owner does a serial write test: writes the backup back with `write_flash 0 stock-backup.bin`, and the device boots stock again.
  5. Owner photographs the board and pads, for `recovery.md`.

  No task may continue to H2 until the owner confirms H1.
- **H2 – First-flash spike.** Upload the `spike` image from Task 11 through the stock web UI "Firmware update". Record:
  - whether stock accepts it
  - the real flash size shown on screen and at `/status`
  - whether pins, colours and backlight look right

  If stock rejects the image or the size limit is too small, **stop and return to the owner** (spec 10.1). Otherwise set the flash layout and `firmware/size-limit.txt` (Task 11 Step 6).
- **H3 – Release gate.** `tools/ota-smoketest.sh` passes against the real device, and a 24 h soak passes (log `/status` every 5 min, heap must not trend down). The results go into the first release notes.

Order: Tasks 1–9 (server, no hardware) → Task 10 → Task 11 → **H1** → **H2** → Tasks 12–13 → Tasks 14–16 → **H3** → tag `v0.1.0`.

---

## File structure

```
VERSION                         single version
CHANGELOG.md
config.example.yaml
docker-compose.yml
Dockerfile                      server image (context = repo root)
server/
  pyproject.toml                package glancebox, ruff + pytest config
  requirements.lock             pinned runtime + dev deps
  glancebox/
    __init__.py                 __version__ from VERSION
    __main__.py                 CLI: serve | render
    config.py                   YAML → AppConfig, ConfigError
    pages.py                    page-type discovery + loading, built-in "url" type
    schedule.py                 pure: which page now, seconds until switch
    render.py                   Playwright wrapper, HTML/URL → baseline JPEG
    frames.py                   FrameStore + refresh worker
    app.py                      FastAPI routes
    templates/base.html         240×240 base layout, inline DejaVu @font-face
    templates/error.html        "no data" frame
    templates/index.html        preview overview
    fonts/                      DejaVu (moved from zugtafel/fonts)
  tests/                        test_config.py, test_pages.py, test_schedule.py,
                                test_render.py, test_frames.py, test_app.py
pages/
  bahn/  page.py, departures.py, template.html, README.md, test_bahn.py
  clock/ page.py, template.html, README.md        (minimal example for authors)
firmware/
  platformio.ini                envs: ultra, spike, native
  size-limit.txt                max .bin bytes for CI
  scripts/version.py            PlatformIO extra script → -DGB_VERSION
  lib/core/                     pure C++17, no Arduino: boot_guard, poll_timing,
                                settings, ota_check (.h/.cpp each)
  test/test_core/               Unity tests for lib/core
  src/                          main.cpp, display.*, frame_client.*, portal.*,
                                web_ui.*, safe_mode.*, i18n.*, spike_main.cpp
tools/
  ota-smoketest.sh
  check_docs_parity.py
  check_fw_size.py
docs/en/, docs/de/              flashing, setup, configuration, writing-pages,
                                updating, recovery (.md each)
docs/RELEASING.md
README.md, README.de.md
.github/workflows/ci.yml, release.yml
```

Removed: `zugtafel/` (the package), `tests/test_zugtafel.py` (ported), `requirements.txt`, `.env.example`. Keep `docs/vorschau.png` as the visual reference for `bahn`.

---

### Task 1: Server skeleton and `bahn` data logic ported

**Files:**
- Create: `VERSION`, `server/pyproject.toml`, `server/requirements.lock`, `server/glancebox/__init__.py`, `pages/bahn/departures.py` (moved), `pages/bahn/test_bahn.py`
- Move: `zugtafel/fonts/*` → `server/glancebox/fonts/`
- Delete: `zugtafel/`, `tests/`, `requirements.txt`, `.env.example`

**Interfaces:**
- Produces: `glancebox.__version__: str` (read from `VERSION`). `pages/bahn/departures.py` keeps the current public API unchanged (`Departure`, `parse`, `parse_directions`, `matches`, `fetch`) with English docstrings and comments. `USER_AGENT = f"glancebox/{version} (+https://github.com/robinlanger/glancebox)"`. `fetch` gains a keyword `user_agent: str`.

- [ ] **Step 1:** `git mv` the departures module and fonts. Port `test_direction_filter_ignores_previous_stops`, `test_clean_train`, `test_parse_skips_arrivals_only` and `test_minutes_until_with_delay_and_midnight` unchanged into `pages/bahn/test_bahn.py`. Drop `test_render_sizes`; it comes back in Task 8. Move `test_bundled_fonts_have_umlauts` to `server/tests/test_fonts.py` with the new path.
- [ ] **Step 2:** `pyproject.toml` sets `[tool.pytest.ini_options] testpaths = ["tests", "../pages"]` and ruff (line length 100). Write `requirements.lock` with exact pins: fastapi, uvicorn, playwright, jinja2, pyyaml, pillow, requests, and for dev pytest, pytest-asyncio, httpx, ruff.
- [ ] **Step 3:** Run `cd server && pip install -r requirements.lock -e . && pytest -q && ruff check . ../pages`. Expected: 5 passed, ruff clean.
- [ ] **Step 4:** Commit: `refactor: restructure repo into glancebox server and bahn page`.

### Task 2: Config loading

**Files:** Create `server/glancebox/config.py`, `server/tests/test_config.py`, `config.example.yaml`

**Interfaces:**
- Produces:
  - `class ConfigError(Exception)`
  - `@dataclass(frozen=True) PageConfig(index: int, type: str, options: dict, duration: int, refresh: int)`
  - `@dataclass(frozen=True) AppConfig(interval: int, timezone: str, lang: str, pages: tuple[PageConfig, ...], pages_dirs: tuple[Path, ...])`
  - `load_config(path: Path) -> AppConfig`
- `duration` defaults to `interval`, and `refresh` defaults to `duration`. `options` = every key except `type`, `duration` and `refresh`. `pages_dirs` = built-in `pages/` plus optional `custom_pages_dir`. `lang` defaults to `de`. Type-specific validation happens in Task 3.

- [ ] **Step 1: Write the failing tests**
  - `test_defaults`: `interval: 30` and one `bahn` page → `duration == 30`, `refresh == 30`, `options == {"station": "X"}`.
  - `test_empty_pages_rejected`: raises `ConfigError` with match `"at least one page"`.
  - `test_yaml_syntax_error_is_config_error`: invalid YAML → `ConfigError` mentioning the file name.
  - `test_duration_must_be_positive`: `duration: 0` → `ConfigError` with match `r"pages\[0\]"`.
- [ ] **Step 2:** `pytest tests/test_config.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `load_config`. `config.example.yaml` mirrors spec 5.5 and has comments.
- [ ] **Step 4:** Tests pass.
- [ ] **Step 5:** Commit: `feat(server): load playlist config from YAML`.

### Task 3: Page types (script pages + built-in `url`)

**Files:** Create `server/glancebox/pages.py`, `server/tests/test_pages.py`, `server/tests/fixtures/pages/{good,broken}/…`

**Interfaces:**
- Consumes: `AppConfig`, `PageConfig`, `ConfigError` (Task 2).
- Produces:
  - `@dataclass PageContext(now: datetime, lang: str, timezone: str)`
  - `class PageType`, with:
    - `name: str`
    - `min_refresh: int`
    - `validate(options: dict) -> None` (raises `ValueError`)
    - `kind: Literal["script", "url"]`
    - `fetch(options, ctx) -> dict` (script only)
    - `template_path: Path` (script only)
  - `load_page_types(dirs: Sequence[Path]) -> dict[str, PageType]`. A later dir overrides an earlier one with the same name.
  - `validate_config(cfg: AppConfig, types: dict[str, PageType]) -> None` raises `ConfigError("pages[<i>] (<type>): <msg>")`.
- Page module contract (document in `writing-pages.md`): `page.py` defines `fetch(options: dict, ctx: PageContext) -> dict`, and optionally `validate(options) -> None` and `MIN_REFRESH: int = 0`. `template.html` sits next to it. Each page dir is imported as a package `glancebox_pages.<name>` via `importlib.util.spec_from_file_location(..., submodule_search_locations=[dir])`, so `from .departures import …` works.
- Built-in `url` type: options `url` (required, http/https), `wait_ms` (default 0), `wait_for` (CSS selector, optional), `timeout_s` (default 15).

- [ ] **Step 1: Write the failing tests**
  - `test_loads_script_page_with_relative_import`: the fixture `good/` uses `from .helper import X`, and `types["good"].fetch({}, ctx)` returns the expected dict.
  - `test_unknown_type_names_index`: config page 1 has `type: nope` → `ConfigError` with match `r"pages\[1\] \(nope\)"`.
  - `test_url_requires_url`: `ConfigError` with match `"url"`.
  - `test_bahn_refresh_below_60_rejected`: real `pages/` dir, `bahn` with `refresh: 10` → `ConfigError` with match `"60"`.
  - `test_broken_page_module_reports_dir`: `broken/page.py` raises at import → `ConfigError` naming `broken`.
  - `test_custom_dir_overrides_builtin`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. `bahn/page.py` needs `MIN_REFRESH = 60` and `validate` for this task. Stub `fetch` with `NotImplementedError`; Task 8 fills it.
- [ ] **Step 4:** Tests pass.
- [ ] **Step 5:** Commit: `feat(server): discover and validate page types`.

### Task 4: Stateless schedule

**Files:** Create `server/glancebox/schedule.py`, `server/tests/test_schedule.py`

**Interfaces:**
- Produces: `select(durations: Sequence[int], available: Sequence[bool], t: float) -> tuple[int | None, float]` returns (page index or `None`, seconds until the next slot switch).
- Algorithm: the cycle is the sum of the durations, and `pos = t mod cycle` gives the slot. If the slot's page is unavailable, walk forward cyclically to the first available page, while the switch time stays that of the current slot. `None` if nothing is available. Also `clamp_next_in(seconds: float) -> int` → round up and clamp to 2–30.

- [ ] **Step 1: Write the failing tests**
  - `test_select_slots`: durations `[30, 15]` → t=0 → `(0, 30)`, t=29 → `(0, 1)`, t=30 → `(1, 15)`, t=45 → `(0, 30)`.
  - `test_select_skips_unavailable`: available `[False, True]` at t=0 → `(1, 30)`.
  - `test_select_none_available` → `(None, 30)`.
  - `test_clamp_next_in`: `0.2→2`, `14.1→15`, `90→30`.
- [ ] **Step 2–4:** Fail, implement, pass.
- [ ] **Step 5:** Commit: `feat(server): stateless time-based page selection`.

### Task 5: Renderer (Chromium → baseline JPEG)

**Files:** Create `server/glancebox/render.py`, `server/glancebox/templates/base.html`, `server/glancebox/templates/error.html`, `server/tests/test_render.py`

**Interfaces:**
- Produces:
  - `MAX_JPEG_BYTES = 24576`
  - `encode_jpeg(png: bytes) -> bytes`: Pillow, RGB, `progressive=False`, `optimize=True`. Quality steps 85, 75, 65, 55, 45, 40 until the size is ≤ `MAX_JPEG_BYTES`, else raise `RenderError`.
  - `class RenderError(Exception)`
  - `class Renderer`, async context manager that keeps one Chromium instance:
    - `async render_html(html: str, timeout_s: float = 10) -> bytes`
    - `async render_url(url: str, wait_ms: int, wait_for: str | None, timeout_s: float) -> bytes`
    - Viewport 240×240, `device_scale_factor=1`. Each render uses a fresh page, closed in `finally`. Every Playwright error and timeout becomes a `RenderError`.
  - `base.html` defines blocks `head` and `body`. It inlines the 4 DejaVu fonts as base64 `@font-face` (build that string once, cached), sets `html,body{margin:0;width:240px;height:240px;overflow:hidden;background:#080a0e;color:#ebeef2}`, and exposes CSS variables for the palette from the old `render.py` (BG, HEADER_BG, FG, MUTED, DIVIDER, ORANGE, RED, YELLOW).

- [ ] **Step 1: Write the failing tests** (mark `@pytest.mark.browser`; CI runs them inside the Docker image)
  - `test_encode_jpeg_baseline_and_size`: noisy 240×240 PNG → result ≤ 24 576 bytes, `Image.open(...).info.get("progressive")` is falsy, size `(240, 240)`.
  - `test_render_html_umlauts`: `"<p>Grüße</p>"` → valid 240×240 JPEG.
  - `test_render_url_timeout_raises`: local `http.server` handler that sleeps 5 s, `timeout_s=1` → `RenderError` in under 3 s.
- [ ] **Step 2–4:** Fail, implement, pass (`playwright install chromium` locally).
- [ ] **Step 5:** Commit: `feat(server): render HTML and URLs to baseline JPEG`.

### Task 6: Frame store and refresh worker

**Files:** Create `server/glancebox/frames.py`, `server/tests/test_frames.py`

**Interfaces:**
- Consumes: `AppConfig`, `PageType`, `PageContext`, `Renderer`, `RenderError`.
- Produces:
  - `@dataclass Frame(jpeg: bytes, etag: str, rendered_at: float)`, with etag = first 16 hex chars of sha1(jpeg) plus a boot nonce.
  - `class FrameStore`:
    - `put(index, jpeg, now)`
    - `get(index, now) -> Frame | None` (`None` when older than **600 s**)
    - `available(now) -> list[bool]`
    - `error_frame: Frame`
  - `async refresh_once(cfg, types, renderer, store, now) -> None` renders every page whose last attempt is older than its `refresh`. Script pages run `fetch` in a thread with a timeout of 20 s, then Jinja renders `template.html` (env loader = page dir + `glancebox/templates`, autoescape on), then `render_html`. URL pages use `render_url`. Exceptions are logged per page and don't stop the other pages.
  - `async run_worker(...)` loops `refresh_once` every 1 s until cancelled.
  - `boot_nonce` is random per process start (Review Focus 4).

- [ ] **Step 1: Write the failing tests** (fake renderer returning fixed bytes, fake clock)
  - `test_refresh_respects_interval`: refresh 60, calls at t=0 and t=30 → 1 render, at t=61 → 2.
  - `test_failing_page_does_not_block_others`: page 0 raises → page 1 still rendered.
  - `test_stale_after_600s`: put at t=0, `get` at t=599 → Frame, at t=601 → `None`.
  - `test_etag_changes_across_store_instances`: same jpeg, two stores → different etags.
- [ ] **Step 2–4:** Fail, implement, pass.
- [ ] **Step 5:** Commit: `feat(server): background frame cache with stale handling`.

### Task 7: HTTP API and CLI

**Files:** Create `server/glancebox/app.py`, `server/glancebox/__main__.py`, `server/glancebox/templates/index.html`, `server/tests/test_app.py`

**Interfaces:**
- Consumes: `select`, `clamp_next_in`, `FrameStore`, `run_worker`, `load_config`, `validate_config`.
- Produces:
  - `create_app(cfg: AppConfig, store: FrameStore, clock: Callable[[], float] = time.time) -> FastAPI`. The lifespan starts the Renderer and worker only when not in test mode.
  - Routes:
    - `GET /api/v1/frame`: 200 or 304 per Global Constraints. When `select` returns `None`, serve the error frame with `X-Next-In: 10`. `X-Next-In` = `clamp_next_in(min(seconds_to_switch, seconds_until_page_refresh))`. Log `id` and `fw` at debug level.
    - `GET /preview/{index}.jpg`: 404 if not rendered yet.
    - `GET /`: HTML list of pages with preview images and last error.
    - `GET /healthz`: 200 with JSON `{"version", "pages_ok": n}`.
  - CLI:
    - `python -m glancebox serve [--config PATH] [--host 0.0.0.0] [--port 8080]`. Config path defaults to env `GLANCEBOX_CONFIG`, else `/config/config.yaml`.
    - `python -m glancebox render <index> -o out.png [--config PATH]` renders one page once.
    - Config errors print the `ConfigError` message and exit 2.

- [ ] **Step 1: Write the failing tests** (FastAPI `TestClient`, store prefilled, fixed clock)
  - `test_frame_200_with_headers`: content type `image/jpeg`, `ETag` set, `2 <= int(X-Next-In) <= 30`.
  - `test_frame_304_on_matching_etag`.
  - `test_stale_etag_after_restart_gets_200`: ETag from another store instance → 200.
  - `test_frame_all_pages_down_returns_error_frame`: empty store → 200 JPEG, `X-Next-In == "10"`.
  - `test_cli_bad_config_exits_2`: `subprocess` run with an unknown type → returncode 2, stderr contains `pages[0]`.
- [ ] **Step 2–4:** Fail, implement, pass.
- [ ] **Step 5:** Commit: `feat(server): frame API, preview UI and CLI`.

### Task 8: `bahn` page (template replaces Pillow drawing)

**Files:** Modify `pages/bahn/page.py`. Create `pages/bahn/template.html`, `pages/bahn/README.md`. Extend `pages/bahn/test_bahn.py`.

**Interfaces:**
- Consumes: `departures.fetch`, `PageContext`.
- Options: `station` (required), `via` (str or list → joined by `,`), `platforms` (str or list), `limit` (1–6, default 4), `title` (default station), `dbf_url` (default `https://dbf.finalrewind.org`), `refresh` (≥ 60).
- `fetch(options, ctx) -> dict` returns:
  - `{"title", "clock": "HH:MM", "rows": [...], "message": str | None, "sub": str | None}`
  - Each row: `{"train", "badge": "s" | "long" | "regional" | "other", "destination", "right", "unit", "right_class": "soon" | "cancelled" | "", "scheduled", "delay", "delay_class": "minor" | "major", "platform", "platform_changed", "cancelled"}`
  - DBF errors are caught: `message = "Keine Daten"`, `sub = "Stand HH:MM"`. An empty list gives `message = "Keine Abfahrten"`.
- Display rules copied from the old `render.py`:
  - badge colours per `_badge_color`
  - `right` is `"fällt aus"` if cancelled, `"jetzt"` if ≤ 0 min, minutes + `"min"` if < 60, else `HH:MM`
  - yellow when ≤ 3 min
  - delay shown only if > 0: orange if < 6, red otherwise
  - platform `"Gl. X"` in orange if changed
  - cancelled destinations struck through in red
  - header 34 px, rows fill 240 − 34 − 6 px, font grows with fewer rows
  - drop the trailing " Hbf" when the destination is too long (CSS `text-overflow: ellipsis` is enough for the rest)
- Must look like `docs/vorschau.png`.

- [ ] **Step 1: Write the failing tests** (monkeypatch `departures.fetch`, fixed `ctx.now`; reuse `SAMPLE` from Task 1)
  - `test_fetch_rows_from_sample`: with `now` 19:49 the `right` values are `["5", "9", "fällt aus"]` (RB75 19:50 +4, S3 19:58 +0, ICE cancelled), the RB75 row has `unit == "min"`, S3 has `platform_changed True`, and ICE has `right_class == "cancelled"`.
  - `test_fetch_dbf_error_gives_message`.
  - `test_template_renders_sample` (`@pytest.mark.browser`): full pipeline → 240×240 JPEG.
- [ ] **Step 2–4:** Fail, implement, pass. Then render via `python -m glancebox render 0 -o /tmp/bahn.png` with live DBF and compare visually against `docs/vorschau.png`. Replace `docs/vorschau.png` with the new render.
- [ ] **Step 5:** Commit: `feat(pages): bahn departures page as HTML template`.

### Task 9: Example page, Docker image, compose

**Files:** Create `pages/clock/{page.py,template.html,README.md}`, `Dockerfile` (rewrite), `docker-compose.yml` (rewrite), `.dockerignore` (update)

**Interfaces:**
- `clock` page: options `lang`. `fetch` returns time, date and weekday. About 15 lines of total logic, written as a teaching example with comments.
- Dockerfile:
  - Base `mcr.microsoft.com/playwright/python:v<same as pinned playwright>-noble`.
  - Copies `VERSION`, `server/` and `pages/`.
  - `pip install -r requirements.lock .`
  - Non-root user, `EXPOSE 8080`.
  - `HEALTHCHECK` curls `/healthz`.
  - `CMD ["python", "-m", "glancebox", "serve"]`.
- Compose: service `glancebox`, port `8080:8080`, mounts `./config.yaml:/config/config.yaml:ro` and `./pages-custom:/config/pages:ro`. `custom_pages_dir: /config/pages` is the documented default in `config.example.yaml`.

- [ ] **Step 1:** Run `docker build -t glancebox:dev .` and `docker run --rm -v $PWD/config.example.yaml:/config/config.yaml:ro -p 8080:8080 glancebox:dev`. Then `curl -s localhost:8080/healthz` and `curl -sI localhost:8080/api/v1/frame`. Expected: healthz 200, frame 200 `image/jpeg` once pages are rendered (≤ 10 s).
- [ ] **Step 2:** Run browser tests inside the image: `docker run --rm glancebox:dev pytest -q -m browser`. Expected: all pass.
- [ ] **Step 3:** Commit: `feat: docker image, compose file and clock example page`.

### Task 10: Firmware core logic (native tests)

**Files:** Create `firmware/platformio.ini`, `firmware/scripts/version.py`, `firmware/lib/core/{boot_guard,poll_timing,settings,ota_check}.{h,cpp}`, `firmware/test/test_core/test_main.cpp`

**Interfaces** (namespace `gb`, C++17, no Arduino headers):
- Boot guard:
  - `struct BootState { uint32_t magic; uint8_t failed; };` with `kBootMagic = 0x47424F58`
  - `struct BootDecision { BootState next; bool safeMode; };`
  - `BootDecision onBoot(BootState rtc)`:
    - an invalid magic counts as fresh, giving `{magic, 1}` and normal mode
    - otherwise `safeMode = rtc.failed >= 3`, and `failed` goes up by 1 (capped at 255)
  - `BootState markHealthy()` → `{magic, 0}`
  - `bool isHealthy(uint32_t uptimeMs, bool wifi, bool web)` → `uptimeMs >= 60000 && wifi && web`
- Poll timing:
  - `uint32_t nextDelayMs(bool ok, int nextInHeader /* -1 if absent */, uint8_t consecutiveFailures)`. On success: `clamp(nextIn, 2, 30) * 1000`, or 10000 if absent. On failure: `min(2000 << (failures-1), 30000)`.
  - `bool showOffline(uint32_t msSinceLastSuccess)` → `>= 120000`.
  - `bool acceptFrameLength(int32_t contentLength)` → `0 < len <= 24576`.
- Settings:
  - `std::optional<std::string> normalizeServerUrl(std::string in, std::string* error)`: trim, add `http://` if there is no scheme, reject `https://` (error `"https_unsupported"`), strip trailing `/`, require a non-empty host.
  - `bool validPassword(const std::string&)` → length ≥ 8.
  - `uint8_t clampBrightness(int)` → 5–100.
- OTA check:
  - `bool isValidMd5Hex(const std::string&)`: 32 hex chars, case-insensitive.
  - `bool looksLikeEsp8266Image(const uint8_t* buf, size_t len)`: `len >= 4 && buf[0] == 0xE9`.
  - `bool fitsOta(size_t imageSize, size_t freeSketchSpace)` → `imageSize <= freeSketchSpace`.
- `platformio.ini`:
  - env `native` (platform native, `test_build_src = no`, lib `core`)
  - env `ultra` (platform `espressif8266@<pin>`, board `esp12e`, framework arduino, `extra_scripts = pre:scripts/version.py`, libs pinned, TFT_eSPI configured entirely via `build_flags` with `USER_SETUP_LOADED` and the pins from Global Constraints, `TFT_CS=-1`, `TFT_SPI_MODE=SPI_MODE3`, `SPI_FREQUENCY=40000000`, `TFT_RGB_ORDER=TFT_BGR`)
  - env `spike` extends `ultra` with `build_src_filter = +<spike_main.cpp> +<display.cpp>`

- [ ] **Step 1: Write the failing Unity tests**, one per function:
  - `test_boot_fresh_magic`
  - `test_boot_third_failure_enters_safe` (failed 0,1,2 → normal; 3 → safe)
  - `test_boot_healthy_resets`
  - `test_is_healthy_needs_all_three`
  - `test_next_delay_success_clamped` (0→2000, 45→30000, -1→10000)
  - `test_next_delay_backoff` (1→2000, 2→4000, 5→30000)
  - `test_show_offline_at_120s`
  - `test_accept_frame_length` (0, 24576, 24577)
  - `test_normalize_server_url_adds_scheme_and_strips_slash` (`" homeserver:8080/ "` → `"http://homeserver:8080"`)
  - `test_normalize_server_url_rejects_https`
  - `test_normalize_server_url_rejects_empty_host` (`"http://"`)
  - `test_valid_password`
  - `test_md5_hex`
  - `test_image_magic`
- [ ] **Step 2:** `cd firmware && pio test -e native`. Expected: build FAIL (undefined symbols).
- [ ] **Step 3:** Implement `lib/core`.
- [ ] **Step 4:** `pio test -e native`. Expected: all PASS.
- [ ] **Step 5:** Commit: `feat(firmware): hardware-independent core logic with native tests`.

### Task 11: Display driver and spike image

**Files:** Create `firmware/src/display.{h,cpp}`, `firmware/src/spike_main.cpp`, `firmware/size-limit.txt`, `tools/check_fw_size.py`

**Interfaces:**
- `display.h`:
  - `void displayBegin(uint8_t brightnessPct)`: init TFT_eSPI, `invertDisplay(true)`, backlight PWM on GPIO5 with inverted duty.
  - `void displaySetBrightness(uint8_t pct)`
  - `bool displayJpeg(const uint8_t* data, size_t len)`: TJpgDec with `setSwapBytes(true)`, output callback pushes each MCU block with `tft.pushImage`.
  - `void displayStatus(const char* title, const char* const* lines, size_t n)`: built-in font, readable at 240 px.
- `spike_main.cpp` (only for H2):
  - connects to Wi-Fi via WiFiManager (AP `GlanceBox-XXXX`)
  - shows version, IP, `ESP.getFlashChipRealSize()` and free heap
  - serves `GET /status` as JSON and `ESP8266HTTPUpdateServer` at `/update`
  - draws a test pattern (R/G/B bars + "Grüße") so colours and orientation can be checked
- `tools/check_fw_size.py <bin> <limit-file>` exits 1 if the bin is larger, and prints both numbers.

- [ ] **Step 1:** `pio run -e spike` and `pio run -e ultra` (ultra may still be a stub `main.cpp` with display init only). Expected: both build.
- [ ] **Step 2:** Write `size-limit.txt` = `450000` (provisional, conservative for 4 MB flash with a 1 MB sketch area). `python tools/check_fw_size.py firmware/.pio/build/spike/firmware.bin firmware/size-limit.txt` → exit 0.
- [ ] **Step 3:** Commit: `feat(firmware): ST7789 display driver and spike image`.
- [ ] **Step 4: STOP → H1 (backup), then H2 (spike).** Report the spike's `.bin` path and size to the owner.
- [ ] **Step 5:** After H2, apply the findings:
  - fix pins and colours if they were wrong
  - set `board_build.ldscript` for the real flash size (keep ≥ 1 MB sketch space)
  - set `size-limit.txt` to `floor(sketch_space / 2) - 32768`
- [ ] **Step 6:** Commit: `fix(firmware): flash layout and size limit from hardware spike`.

### Task 12: Settings, captive portal, device web UI, OTA endpoint

**Files:** Create `firmware/src/portal.{h,cpp}`, `firmware/src/web_ui.{h,cpp}`, `firmware/src/i18n.{h,cpp}`

**Interfaces:**
- Consumes: `gb::normalizeServerUrl`, `gb::validPassword`, `gb::clampBrightness`, `gb::isValidMd5Hex`, `gb::looksLikeEsp8266Image`, `gb::fitsOta`, `gb::markHealthy`, display functions.
- `struct Settings { char serverUrl[96]; char updatePassword[33]; uint8_t brightness; };`
  - `bool settingsLoad(Settings&)` / `bool settingsSave(const Settings&)`: LittleFS file `/settings.json`, written only on change.
- `void portalRun(Settings&)`: WiFiManager with extra fields for server URL, update password and brightness. It validates with core functions and shows the AP name and instructions on the display. It blocks until configured.
- `void webUiBegin(Settings&, const StatusProvider&)` registers:
  - `GET /`: status and settings form, text DE/EN via `i18n` by `Accept-Language`
  - `POST /settings` (Basic auth)
  - `POST /restart` (Basic auth)
  - `POST /reset` (Basic auth): clears Wi-Fi and settings
  - `GET /status`: JSON `{version, uptime_s, heap_free, rssi, boot_failed, safe_mode, frames_ok, last_frame_age_s, flash_size}`
  - `POST /update` (Basic auth, multipart fields `md5` then `firmware`):
    - missing or invalid md5 → 400
    - first chunk fails `looksLikeEsp8266Image` → abort with 400
    - `Update.begin(size)` uses `fitsOta`
    - `Update.setMD5(md5)`
    - on `Update.end(true)` success, write `markHealthy()` to RTC, respond 200, restart after 1 s
    - any failure → `Update.end(false)` path, 400/500 with reason, device keeps running
- `void webUiLoop()`

- [ ] **Step 1:** `pio run -e ultra` builds. `pio test -e native` still passes.
- [ ] **Step 2:** On device (after H2, flashed via the spike's `/update`):
  - the portal appears on first boot
  - the URL `homeserver:8080/` is saved as `http://homeserver:8080`
  - `curl -u admin:<pw> -F md5=000…0 -F firmware=@firmware.bin http://<ip>/update` → 400 and the device stays up
  - with the correct md5 → 200, reboot, `/status` shows the same version
- [ ] **Step 3:** Commit: `feat(firmware): captive portal, web UI and verified OTA`.

### Task 13: Main loop, frame client, safe mode, watchdog

**Files:** Create `firmware/src/main.cpp` (replace stub), `firmware/src/frame_client.{h,cpp}`, `firmware/src/safe_mode.{h,cpp}`

**Interfaces:**
- Consumes: everything from Tasks 10–12.
- `setup()` order is mandatory:
  1. read RTC (`ESP.rtcUserMemoryRead`), `gb::onBoot`, write back
  2. if `safeMode` → `safeModeRun()` (never returns)
  3. display, boot status screen (version and IP), settings, Wi-Fi or portal, web UI
- `safeModeRun()`:
  - Wi-Fi from saved credentials, AP fallback
  - web UI limited to `/status`, `/update`, `/restart` and `POST /boot-normal` (writes `markHealthy()` and restarts)
  - status screen "Safe mode", IP, failed count
  - must not link `frame_client` or TJpgDec code paths
- `frame_client`:
  - a `static uint8_t frameBuf[24576]` allocated once
  - `FrameResult fetchFrame(const char* serverUrl, const char* etag)` (HTTPClient, timeout 8 s, `Content-Length` checked with `gb::acceptFrameLength`, reads into `frameBuf`)
  - returns `{status, len, etag, nextIn}`
  - `loop()` uses `gb::nextDelayMs`, `gb::showOffline` and `gb::isHealthy` (once true, write `markHealthy()` to RTC once)
- Watchdog: keep the default HW and SW WDT, call `yield()` in long loops. `/status` reports `ESP.getResetReason()`.
- No `String` concatenation in the poll loop. ETag goes into a fixed `char[40]`.

- [ ] **Step 1:** `pio run -e ultra`, then `python tools/check_fw_size.py …` → exit 0.
- [ ] **Step 2:** On device:
  - frames rotate according to `config.example.yaml`
  - stop the server → offline screen after about 120 s, recovers when the server is back
- [ ] **Step 3:** Safe-mode test on device. Build with `-DGB_CRASH_TEST` (an `abort()` at 5 s uptime, guarded by the flag) and flash it via OTA. After the 3rd crash, safe mode appears. Re-flash the normal image via `/update`, and it boots normal.
- [ ] **Step 4:** Commit: `feat(firmware): frame loop, offline screen and boot-loop safe mode`.

### Task 14: CI

**Files:** Create `.github/workflows/ci.yml`, `tools/check_docs_parity.py`

**Interfaces:**
- `check_docs_parity.py` exits 1 when:
  - a file exists in only one of `docs/en`/`docs/de`, or `README.md` exists without `README.de.md`
  - the heading level sequence (`#` counts, in order) differs between a file and its counterpart
- Jobs, with `actions/*` pinned by tag:
  - `server`: ruff, then pytest without `-m browser`
  - `server-image`: docker build, then `pytest -m browser` inside the image
  - `firmware`: cache `~/.platformio`, run `pio test -e native`, `pio run -e ultra -e spike` and `check_fw_size.py`, upload the bin as an artifact
  - `docs`: parity check

- [ ] **Step 1:** Write a test for the parity script, `server/tests/test_docs_parity.py`, against temp dirs: matching → 0, missing file → 1, heading mismatch → 1. Fail, implement, pass.
- [ ] **Step 2:** Push the branch. All 4 jobs are green (`gh run list --branch glancebox`).
- [ ] **Step 3:** Commit: `ci: test server, firmware and docs on every push`.

### Task 15: Release pipeline and OTA smoketest

**Files:** Create `.github/workflows/release.yml`, `tools/ota-smoketest.sh`, `docs/RELEASING.md`, `CHANGELOG.md`

**Interfaces:**
- `release.yml` on tag `v*`:
  - fail if the tag ≠ `v$(cat VERSION)`
  - build the firmware, write `glancebox-ultra-<ver>.bin` plus `.md5` and `.sha256`
  - buildx push `ghcr.io/robinlanger/glancebox:<ver>` and `:latest` (amd64, arm64)
  - `gh release create` with the bins and the `CHANGELOG.md` section for the version
- `ota-smoketest.sh <device-ip> <new.bin> <previous.bin>`:
  - env `GB_PASSWORD`, `set -euo pipefail`, curl and jq only, non-interactive
  - steps exactly per spec 5.4 point 4:
    1. read the version
    2. wrong MD5 → expect 400 and the same version, still up
    3. new → wait up to 90 s → version matches, `boot_failed == 0`, `frames_ok` increases within 60 s
    4. previous → verify
    5. new again → verify
  - prints `PASS`/`FAIL <step>`, exit code 0/1
  - the version to expect is read from the bin with `strings | grep` against the `GB_VERSION` marker `GBVER:<ver>`; the firmware embeds that literal
- `RELEASING.md` is a checklist:
  1. bump `VERSION` and `CHANGELOG`
  2. CI green
  3. smoketest on real hardware with the previous release bin
  4. 24 h soak result
  5. tag
  6. note the smoketest result in the release notes
  7. a section "Running the smoketest in a self-hosted runner"

- [ ] **Step 1:** `shellcheck tools/ota-smoketest.sh` is clean. Run the release workflow on a test tag in a fork or with `act`, or document `workflow_dispatch` dry-run mode (`push: false`) and run that. Expected: artifacts built.
- [ ] **Step 2:** Commit: `ci: release pipeline, OTA smoketest and release checklist`.

### Task 16: Documentation (EN + DE)

**Files:** Rewrite `README.md`. Create `README.de.md`, `docs/{en,de}/{flashing,setup,configuration,writing-pages,updating,recovery}.md`

Content per spec section 7:
- **README:** what it is (photo `docs/vorschau.png`), the hardware requirement, the warning "no way back to stock firmware without a serial backup", a quickstart (compose + first flash link), a link to the other language at the top, credits to DBF/derf and the ESPHome community for the pinout.
- **`flashing.md`:**
  - optional but recommended backup (H1 procedure, with Pico `debugprobe` and CH340 variants)
  - stock web UI upload
  - what you see on first boot
- **`recovery.md`:**
  - safe mode
  - power-cycle resets the counter
  - serial flash with the owner's board photo and pad labels from H1
  - restoring the backup
- **`writing-pages.md`:**
  - the page contract from Task 3
  - the `clock` example walkthrough
  - the `url` page tips (design for 240×240, `wait_for`)
  - `/` preview UI
  - the `render` CLI

- [ ] **Step 1:** `python tools/check_docs_parity.py` → exit 0.
- [ ] **Step 2:** Follow `README.md` quickstart on a clean checkout. Every command works as written.
- [ ] **Step 3:** Commit: `docs: bilingual user documentation`.

### Final: H3 and v0.1.0

- [ ] Owner runs H3 (smoketest + 24 h soak). Because there is no previous release yet, the smoketest's "previous" image is the same commit built with `VERSION` = `0.1.0-prev`, which proves the image can replace itself.
- [ ] Owner renames the GitHub repo to `robinlanger/glancebox`. Update `git remote set-url origin git@github.com:robinlanger/glancebox.git`.
- [ ] Tag `v0.1.0` and push the tag. The release workflow is green.
