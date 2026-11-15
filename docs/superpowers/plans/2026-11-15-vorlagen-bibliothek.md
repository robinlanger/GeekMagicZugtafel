# Template Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ready-made pages you only add to `config.yaml`: `weather` (Open-Meteo), `kuma` (Uptime Kuma status page), `ai` (AI usage limits, one provider per page). Plus the shared base they need and a click-through template catalog in the docs.

**Architecture:** Each template is a script page under `pages/<type>/`, following the pattern of `bahn` and `clock`. The server gains four shared pieces:
- Jinja UI macros (`ui.html`) for one common look.
- `${VAR}` expansion in the YAML, so secrets live in `.env`.
- A small HTTP helper.
- A key-protected push inbox (`POST /api/v1/push/<channel>`), held in RAM only. Pages read it through `ctx.pushed(channel)`. Only channels and top-level keys that a page type declares in `PUSH_KEYS` are accepted.

The Claude subscription limit arrives through the inbox from a Claude Code status-line script.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, requests, Playwright/Chromium (render), pytest. POSIX sh + curl and PowerShell for the status-line script.

**Spec:** `docs/superpowers/specs/2026-11-15-vorlagen-bibliothek-design.md`

## Global Constraints

- Page types are named `weather`, `kuma` and `ai` (the spec leaves names to the builder). The `ai` page selects its source with `provider:`. Allowed values: `claude`, `anthropic-api`, `openai-api`, `xai-api`, plus `copilot` only if Task 9 confirms an official route.
- Every page supports `lang` `de` and `en` (page option, else the top-level `lang`). All visible text exists in both languages.
- **Look:**
  - Header 34 px with title on the left (bold 16 px) and clock on the right (bold 18 px).
  - Header background `--header-bg`, or `--header-alert` `rgb(150,25,25)` on a failure.
  - Keep the bottom 8 px free.
  - New CSS variables in `base.html`: `--green: rgb(60,200,110)`, `--blue: rgb(90,160,255)`, `--header-alert: rgb(150,25,25)`.
- **Bar colour by fill level:** green below 75 %, orange (`--orange`) from 75 %, red (`--red`) from 90 %.
- Secrets never appear in `config.yaml` literally. The docs always show `${NAME}` together with `.env`.
- **Push inbox:** only on the home network (LAN). The docs must never describe exposing it to the internet.
  - Without `push_key` the endpoint answers 404.
  - The body is a JSON object of at most 65 536 bytes.
  - Channel names match `^[a-z0-9_-]{1,32}$`.
  - Only keys a page declares in `PUSH_KEYS` are stored. Nothing is written to disk. Bodies are never logged.
- Every network call goes through `glancebox.http.get_json` (sets a timeout and the User-Agent `glancebox/<version>`). No network access in tests.
- Status pages never show a stale "all OK". When `kuma` and `ai` have no data, they show the notice immediately (in orange for `kuma`) instead of keeping the last image. `weather` raises on error, so the last image stays for up to 10 min.
- Only official, documented provider APIs. No CLI login tokens on the server.
- Docs exist in EN and DE with the same heading structure (`tools/check_docs_parity.py`, extended to subfolders in Task 4).
- Every non-browser test passes with `cd server && pytest -q -m "not browser"`. Ruff is clean with `ruff check . ../pages`. Browser tests run inside the image with `docker compose build && docker run --rm glancebox:dev pytest -q -m browser`.

## Review Focus

1. **A `${VAR}` that is set but empty, or that sits inside a longer string (`http://${HOST}:3001`).** The empty one is an error that names the variable. The partial one stays literal text (expansion applies only when the whole value is `${NAME}`), and the docs say so. Tested in Task 1.
2. **Pushes with a wrong or missing key, a too-large body, a non-object JSON body, or an undeclared channel.** These give 401, 401, 413, 422 and 404 respectively, and the stored value stays unchanged. A key comparison that leaks timing is unacceptable. Tested in Task 3.
3. **Kuma with 0 monitors, every monitor down, or only pending/maintenance monitors, and a down monitor whose whole heartbeat list is down.**
   - 0 monitors gives the notice "No monitors".
   - All down shows at most 4 rows plus "+ N more".
   - Pending or maintenance never makes the header red.
   - A down monitor with no up beat shows "≥ X min".

   Tested in Task 6.
4. **The Claude `resets_at` already passed, a `rate_limits` key missing (plans without a weekly window, or an older Claude Code), or no push since the server started.** These give 0 % with "reset", only the windows that exist, and the notice "No data yet" respectively. Tested in Task 7.
5. **Weather around midnight and DST.** The "next 4 full hours" are the 4 hourly slots after the current hour, in the configured time zone, even across midnight. Tested in Task 5.

---

### Task 1: `${VAR}` in config, `push_key`, `.env` in compose

**Files:**
- Modify: `server/glancebox/config.py` (`_TOP_LEVEL_KEYS`, `AppConfig`, `load_config`)
- Modify: `docker-compose.yml`, `config.example.yaml`, `docs/en/configuration.md`, `docs/de/configuration.md`
- Test: `server/tests/test_config.py`

**Interfaces:**
- Produces: `expand_env(value: Any, where: str, environ: Mapping[str, str]) -> Any` in `config.py`. It walks dicts and lists recursively. Every `str` that matches `^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$` is replaced by `environ[name]`. A missing or empty variable raises `ConfigError(f"{where}: environment variable {name} is not set")`, where `where` is the YAML path, for example `pages[2].token`. `load_config` applies it to the whole parsed document with `os.environ` before any validation.
- Produces: `AppConfig.push_key: str | None = None`. It is a new **last** field with a default, so existing positional constructions keep working. It comes from the top-level key `push_key`, which must be a non-empty string of at least 16 characters, else `ConfigError`.

- [ ] **Step 1: Write the failing tests**

```python
def test_env_whole_value_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("KUMA_URL", "http://kuma.lan:3001")
    cfg = load_config(write(tmp_path, "pages:\n  - type: clock\n    url: ${KUMA_URL}\n"))
    assert cfg.pages[0].options["url"] == "http://kuma.lan:3001"

def test_env_inside_longer_string_stays_literal(tmp_path, monkeypatch):
    monkeypatch.setenv("HOST", "x")
    cfg = load_config(write(tmp_path, "pages:\n  - type: clock\n    url: http://${HOST}:1\n"))
    assert cfg.pages[0].options["url"] == "http://${HOST}:1"

@pytest.mark.parametrize("value", [None, ""])
def test_env_missing_or_empty_names_path_and_variable(tmp_path, monkeypatch, value):
    monkeypatch.delenv("NOPE", raising=False)
    if value is not None:
        monkeypatch.setenv("NOPE", value)
    with pytest.raises(ConfigError, match=r"pages\[0\]\.token: environment variable NOPE"):
        load_config(write(tmp_path, "pages:\n  - type: clock\n    token: ${NOPE}\n"))

def test_push_key_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GLANCEBOX_PUSH_KEY", "k" * 32)
    cfg = load_config(write(tmp_path, "push_key: ${GLANCEBOX_PUSH_KEY}\npages:\n  - type: clock\n"))
    assert cfg.push_key == "k" * 32

def test_push_key_too_short(tmp_path):
    with pytest.raises(ConfigError, match="push_key"):
        load_config(write(tmp_path, "push_key: short\npages:\n  - type: clock\n"))

def test_push_key_default_none(tmp_path):
    assert load_config(write(tmp_path, "pages:\n  - type: clock\n")).push_key is None
```

`write(tmp_path, text)` is the existing helper in `test_config.py`, or a two-line one if it has none.

- [ ] **Step 2: Run them and verify they fail.** `cd server && pytest tests/test_config.py -q` must FAIL on the new tests.
- [ ] **Step 3: Implement `expand_env` and `push_key`** in `config.py` as described under Interfaces.
- [ ] **Step 4: Compose and example.**
  - In `docker-compose.yml`, add under the service:
    ```yaml
    env_file:
      - path: .env
        required: false
    ```
    with a comment that secrets go there and that `docker compose up -d` (not `restart`) applies changes to `.env`.
  - In `config.example.yaml`, add a commented line: `# push_key: ${GLANCEBOX_PUSH_KEY}   # only needed for pushed data (ai page, provider claude)`.
- [ ] **Step 5: Docs (EN and DE `configuration.md`).**
  - Add a section "Secrets and environment variables". It covers whole-value `${NAME}`, the `.env` file next to `docker-compose.yml`, `up -d` versus `restart`, and the error on a missing variable.
  - Add `push_key` to the top-level table: needed for pushed data, generate it with `openssl rand -hex 24`, LAN only.
- [ ] **Step 6: Run tests and docs parity.** Run `cd server && pytest -q -m "not browser" && ruff check . ../pages && python3 ../tools/check_docs_parity.py`. All must pass.
- [ ] **Step 7: Commit.** `git commit -m "feat(server): \${VAR} in config, push_key, .env for compose"`

---

### Task 2: Shared UI macros and the HTTP helper

**Files:**
- Create: `server/glancebox/templates/ui.html`, `server/glancebox/http.py`
- Modify: `server/glancebox/templates/base.html` (CSS variables and classes for the macros)
- Modify: `docs/en/writing-pages.md`, `docs/de/writing-pages.md`
- Test: `server/tests/test_ui.py`, `server/tests/test_http.py`

**Interfaces:**
- Produces: these Jinja macros in `ui.html`. Templates use them with `{% import "ui.html" as ui %}`. The CSS for their classes lives in `base.html`.
  - `ui.header(title, clock, alert=False)` renders `<div class="ui-hdr[ ui-alert]">` with `.ui-title` and `.ui-clock`, in the look from Global Constraints.
  - `ui.notice(message, sub=None, tone="muted")`, where `tone` is `muted`, `warn` (orange) or `bad` (red), renders a box centred below the header (`top:34px; height:198px`).
  - `ui.bar(percent, text, height=30)` renders a track in `--divider` with a fill of `width:{{ [[percent,0]|max,100]|min }}%`. The fill has class `ui-ok`, `ui-warn` or `ui-bad` by the thresholds (75 and 90). `text` sits right-aligned inside the bar.
  - `ui.level(percent)` returns the class name alone, for pages that colour text.
- Produces: `glancebox.http.get_json(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float = 10) -> Any`. It uses `requests.get`, adds `User-Agent: glancebox/<__version__> (+https://github.com/robinlanger/glancebox)` on top of the caller's headers, calls `raise_for_status()` and returns `.json()`. Pages call it as `from glancebox import http` and then `http.get_json(...)`, so tests can monkeypatch `glancebox.http.get_json`.

- [ ] **Step 1: Write the failing tests.**
  - In `test_ui.py`, render a small inline template through `glancebox.frames._jinja_env([])` and assert:
    - `ui.bar(74, "x")` contains `ui-ok`, `ui.bar(75, "x")` contains `ui-warn` and `ui.bar(90, "x")` contains `ui-bad`.
    - `ui.bar(130, "x")` contains `width:100%` and `ui.bar(-5, "x")` contains `width:0%`.
    - `ui.header("T", "14:05", alert=True)` contains `ui-alert`.
    - `ui.notice("<b>")` is HTML-escaped.
  - In `test_http.py`, monkeypatch `requests.get` with a fake that records its kwargs and assert:
    - `timeout == 10`, and the User-Agent starts with `glancebox/`.
    - Caller headers are kept.
    - `raise_for_status` is called, so an HTTPError propagates.
- [ ] **Step 2: Run them and verify they fail.** `cd server && pytest tests/test_ui.py tests/test_http.py -q` must FAIL.
- [ ] **Step 3: Implement** `ui.html`, the `base.html` CSS and `http.py`.
- [ ] **Step 4: Docs.**
  - In `writing-pages.md` (EN and DE), add a section "Building blocks" that shows `{% import "ui.html" as ui %}` with each macro in one line plus an example, and lists the new CSS variables.
  - In the page-contract section, add a sentence recommending `glancebox.http.get_json` for network calls.
- [ ] **Step 5: Run tests and parity.** Run them as in Task 1 Step 6. All must pass.
- [ ] **Step 6: Commit.** `git commit -m "feat(server): shared UI macros and HTTP helper for pages"`

---

### Task 3: Push inbox

**Files:**
- Create: `server/glancebox/push.py`
- Modify: `server/glancebox/pages.py` (`PageContext`, `PageType`, `_load_script_page`)
- Modify: `server/glancebox/frames.py` (`render_page`, `refresh_once`, `run_worker` take the inbox)
- Modify: `server/glancebox/app.py` (create the inbox, add the endpoint, pass it to the worker)
- Modify: `server/glancebox/__main__.py` (the `render` command passes an empty inbox)
- Modify: `docs/en/writing-pages.md`, `docs/de/writing-pages.md`
- Test: `server/tests/test_push.py`, plus additions to `server/tests/test_app.py`

**Interfaces:**
- Produces, in `push.py`:
  - `@dataclass(frozen=True) class Pushed: data: dict; received_at: float`.
  - `class PushInbox` with `put(channel: str, data: dict, now: float) -> None` and `get(channel: str) -> Pushed | None`. It uses a `threading.Lock`, because the endpoint runs in the threadpool and `fetch` in worker threads.
  - `CHANNEL_RE = re.compile(r"^[a-z0-9_-]{1,32}$")` and `MAX_BODY = 65536`.
- Produces: an optional page module attribute `PUSH_KEYS: dict[str, tuple[str, ...]]`, mapping each channel to the top-level JSON keys to keep. `PageType.push_keys` holds it, defaulting to `{}`. `_load_script_page` validates the form and raises `ConfigError` on bad channel names or non-string keys. `merge_push_keys(types: dict[str, PageType]) -> dict[str, frozenset[str]]` in `pages.py` merges these across all types.
- Produces: `PageContext.pushed: Callable[[str], Pushed | None] = field(default=lambda _c: None)` as a new last field, so existing constructions still work. `render_page(..., inbox: PushInbox | None = None)` fills it with `inbox.get`, or keeps the default.
- Produces: `POST /api/v1/push/{channel}`. The checks run in this order:
  1. No `cfg.push_key` → 404.
  2. Channel not in the merged `PUSH_KEYS` or not matching `CHANNEL_RE` → 404.
  3. Header `Authorization: Bearer <key>` missing or wrong → 401, compared with `secrets.compare_digest`.
  4. `Content-Length` above `MAX_BODY`, or the body actually read longer → 413.
  5. Body not a JSON object → 422.
  6. Otherwise store `{k: body[k] for k in allowed if k in body}` with `clock()` and answer **204**.
- `create_app` builds the allowlist from `types`. Without `types` it is empty. `run_worker(cfg, types, renderer, store, inbox)` forwards the inbox.
- Re-render: none is triggered. A push page picks up new data on its next `refresh` (decision: the spec leaves this to the builder, and pages that read pushes need no network, so `refresh: 30` is cheap). The docs recommend `refresh: 30`.

- [ ] **Step 1: Write the failing tests** in `test_push.py`. Use `TestClient` and a fake page type with `push_keys={"claude": ("rate_limits",)}`. Assert each case:
  - Correct key → 204, and `inbox.get("claude").data == {"rate_limits": {...}}` (the extra key `cwd` is dropped). `received_at` equals the fake clock.
  - No `push_key` in the config → 404.
  - Unknown channel `foo` → 404.
  - Channel `Claude!` → 404.
  - Wrong key → 401.
  - No `Authorization` header → 401.
  - A body of 70 000 bytes → 413.
  - Body `[1,2]` → 422.
  - Invalid JSON → 422.

  After every rejected request, the previously stored value is unchanged.

  Also add `test_page_ctx_pushed`: `render_page` with an inbox and a fake renderer that captures the HTML hands `ctx.pushed("claude")` to `fetch`.
- [ ] **Step 2: Run them and verify they fail.** `cd server && pytest tests/test_push.py -q` must FAIL.
- [ ] **Step 3: Implement** `push.py` and the changes in `pages.py`, `frames.py`, `app.py` and `__main__.py`.
- [ ] **Step 4: Docs** (`writing-pages.md`, EN and DE). Add a section "Data pushed to the server" covering:
  - `PUSH_KEYS`, `ctx.pushed(channel)` returning `.data` and `.received_at`.
  - The endpoint and its status codes, plus a curl example.
  - Data lives in RAM only, so it is gone after a restart.
  - LAN only.
- [ ] **Step 5: Run the whole suite and parity.** All must pass.
- [ ] **Step 6: Commit.** `git commit -m "feat(server): key-protected push inbox for pages"`

---

### Task 4: Template catalog skeleton, parity in subfolders, preview tool

**Files:**
- Modify: `tools/check_docs_parity.py` (pair files recursively under `docs/en` and `docs/de`)
- Create: `docs/en/templates/README.md`, `docs/de/templates/README.md` (the catalog)
- Create: `docs/en/templates/bahn.md`, `docs/en/templates/clock.md`, and the same two under `docs/de/templates/`
- Create: `tools/render_previews.py`, `docs/img/templates/` (PNG previews)
- Modify: the documentation tables in `README.md` and `README.de.md`; a link from `configuration.md` (EN and DE)
- Test: `server/tests/test_docs_parity.py` (extend it)

**Interfaces:**
- Produces, catalog layout: sections in this order, each entry with a preview image, one line of text and a link:
  - "Time & weather": `clock`, `weather`
  - "Server & smart home": `kuma`
  - "AI & development": `ai`
  - "Transport": `bahn`
  - "Your own pages", linking to `writing-pages.md`

  The German headings are "Zeit & Wetter", "Server & Smart Home", "KI & Entwicklung", "Verkehr" and "Eigene Seiten".
- Produces, the structure of every template page, H2 headings in this order: What it shows · What you need · Example · Options (table) · Setup · Privacy & security · When something is wrong. Later tasks follow it.
- Produces: `tools/render_previews.py`. It holds `SAMPLES: dict[str, tuple[str, dict, dict]]`, mapping a preview name to the page type, its options and the data dict handed to the template. It renders each entry through `frames._jinja_env` and `Renderer.render_html` to `docs/img/templates/<name>.png` (PNG converted from the JPEG). Run it inside the image: `docker run --rm -v "$PWD/docs/img:/app/docs/img" glancebox:dev python /app/tools/render_previews.py`. The Dockerfile does not copy `tools/`, so mount it with `-v "$PWD/tools:/app/tools:ro"`. Later tasks add their samples here.

- [ ] **Step 1: Write the failing test** in `test_docs_parity.py`. Build a temporary tree with `docs/en/templates/x.md` but no German counterpart. `main` must return 1 and print `docs/de/templates/x.md is missing`. A matching pair returns 0.
- [ ] **Step 2: Run it and verify it fails.**
- [ ] **Step 3: Implement** recursive pairing (`rglob("*")`, files only, compared by relative path).
- [ ] **Step 4: Write the catalog README and the `bahn` and `clock` pages** in EN and DE, with content from `pages/*/README.md` and `configuration.md` in the agreed structure. The `pages/*/README.md` files stay as short developer notes and gain one line linking to the catalog page.
- [ ] **Step 5: Write `render_previews.py`** with samples for `clock` and `bahn` (data in the shape their `fetch` returns, taken from the existing tests). Render them and commit the PNGs.
- [ ] **Step 6: Run tests and parity.** All must pass. Click through the catalog links in the GitHub preview, or check the relative paths by hand.
- [ ] **Step 7: Commit.** `git commit -m "docs: template catalog, recursive EN/DE parity, preview renderer"`

---

### Task 5: Template `weather`

**Files:**
- Create: `pages/weather/page.py`, `pages/weather/template.html`, `pages/weather/icons.html` (SVG macros), `pages/weather/README.md`, `pages/weather/test_weather.py`
- Create: `docs/en/templates/weather.md`, `docs/de/templates/weather.md`
- Modify: the catalog READMEs, `tools/render_previews.py`, `README.md` and `README.de.md` (Credits: Open-Meteo, CC BY 4.0)

**Interfaces:**
- Consumes: `glancebox.http.get_json`, the `ui.header` macro.
- Options: either `location: <name>` or both `latitude` and `longitude`, never both forms (`validate` raises `ValueError`). Optional `title` (default: the geocoded name, or `location`, or `"Wetter"`/`"Weather"`) and `lang`. `MIN_REFRESH = 900`.
- Geocoding: `https://geocoding-api.open-meteo.com/v1/search` with `name`, `count=1`, `language=<lang>` and `format=json`. Take `results[0]`'s `latitude`, `longitude` and `name`. No results raises `ValueError("location not found: …")`. Successful lookups are cached in a module-level dict keyed by `(location, lang)`.
- Forecast: `https://api.open-meteo.com/v1/forecast` with these parameters:
  - `latitude`, `longitude`
  - `current=temperature_2m,weather_code,is_day`
  - `hourly=temperature_2m,precipitation_probability,weather_code,is_day`
  - `daily=temperature_2m_max,temperature_2m_min`
  - `timezone=<ctx.timezone>`, `forecast_days=2`
- `fetch` returns:
  ```
  {"title", "clock": "HH:MM", "icon": str, "temp": int, "desc": str, "high": int, "low": int,
   "hours": [{"hour": "15", "temp": int, "rain": int}] * 4}
  ```
  Temperatures are rounded half-up. `hours` holds the first 4 hourly entries whose start is after the current hour.
- Icon keys come from the WMO code:
  - `clear` (0), `partly` (1, 2), `cloudy` (3), `fog` (45, 48)
  - `rain` (51–67, 80–82), `snow` (71–77, 85, 86), `thunder` (95–99)
  - `clear` and `partly` become `clear-night` and `partly-night` when `is_day == 0`.
  - Unknown codes become `cloudy`.

  Descriptions per code exist in DE and EN, for example 0 "Klar"/"Clear", 2 "Leicht bewölkt"/"Partly cloudy", 61 "Leichter Regen"/"Light rain".
- Layout C, as in the spec: icon about 70×56 at left, temperature 46 px bold, description muted 13 px, then `↑ high` in `--red` and `↓ low` in `--blue`, then a row of 4 columns (hour muted, temperature bold, rain % in `--blue` 11 px) below a divider.
- Errors: `fetch` lets exceptions propagate, so the last image stays for 10 min (Global Constraints).

- [ ] **Step 1: Write the failing tests** in `test_weather.py`, using recorded JSON responses as Python dicts in the test file and monkeypatching `glancebox.http.get_json`. Pin the 4 hours by the hourly time strings, not by index arithmetic.
  - `test_validate_location_xor_coordinates`: both forms → ValueError, neither → ValueError, latitude 91 → ValueError.
  - `test_fetch_maps_current_and_hours`: with `now` 14:05 the hours are `15, 16, 17, 18`, plus temperatures, rain and the description in DE.
  - `test_hours_cross_midnight`: with `now` 22:30 the hours are `23, 00, 01, 02`.
  - `test_night_icon`: `is_day=0` with code 0 gives `clear-night`.
  - `test_geocode_cached`: two fetches make one geocoding call.
  - `test_location_not_found` raises.
  - `test_english_texts`.
  - `@pytest.mark.browser test_template_renders` renders through `render_page` with a real `Renderer`. The result is a 240×240 JPEG.
- [ ] **Step 2: Run them and verify they fail.**
- [ ] **Step 3: Implement** `page.py`, `icons.html` (one macro `icon(key, w, h)` with simple flat SVGs: sun, moon, cloud, rain drops, snowflake, lightning, fog lines) and `template.html`.
- [ ] **Step 4: Run the tests and verify they pass.** Run the browser test inside the image.
- [ ] **Step 5: Docs and preview.**
  - Write `templates/weather.md` (EN and DE) in the Task 4 structure. It has no secrets. Mention the 15-minute minimum and that it is a free service.
  - Add a catalog entry, `README.md` for the page and a preview sample, then render the PNG.
  - Add the commented example to `config.example.yaml`: `- type: weather` with `location: Frankfurt am Main`.
- [ ] **Step 6: Run the whole suite and parity.** All must pass.
- [ ] **Step 7: Commit.** `git commit -m "feat(pages): weather template (Open-Meteo)"`

---

### Task 6: Template `kuma`

**Files:**
- Create: `pages/kuma/page.py`, `pages/kuma/template.html`, `pages/kuma/README.md`, `pages/kuma/test_kuma.py`
- Create: `docs/en/templates/kuma.md`, `docs/de/templates/kuma.md`
- Modify: the catalog, `tools/render_previews.py` (samples `kuma-ok` and `kuma-down`), `config.example.yaml`

**Interfaces:**
- Consumes: `http.get_json`, the macros `ui.header` (with `alert`) and `ui.notice`.
- Options: `url` (http/https, required), `slug` (required, `^[a-z0-9-]+$`), optional `title` and `lang`. No `MIN_REFRESH`; the docs recommend `refresh: 30`.
- Sources:
  - `GET {url}/api/status-page/{slug}` gives `config.title` and `publicGroupList[].monitorList[]` with `id` and `name`.
  - `GET {url}/api/status-page/heartbeat/{slug}` gives `heartbeatList[str(id)]` (beats oldest first, each with `status`, `time` and `msg`) and `uptimeList["{id}_24"]` (fraction 0–1).
  - Status codes: 0 down, 1 up, 2 pending, 3 maintenance.
  - **Before writing fixtures,** read `server/routers/status-page-router.js` of Uptime Kuma 2.0.x on GitHub and copy the exact response shape and the `time` format. 1.23 writes `"YYYY-MM-DD HH:MM:SS.sss"` in UTC. Parse both that format and ISO 8601, treating values without a zone as UTC.
- A monitor's state is the status of its last beat. A monitor with no beats counts as pending.
- `fetch` returns:
  ```
  {"title", "clock", "state": "ok"|"down"|"error"|"empty",
   "up": int, "total": int, "uptime": "99,9 %"|"99.9 %"|None, "pending": int,
   "down": [{"name", "since": "12 min"|"3 h"|"2 d"|"≥ 40 min"}][:4], "more": int,
   "message", "sub"}
  ```
  - `up` counts status 1 and 3.
  - `uptime` is the mean of the `_24` values over all monitors, formatted with 1 decimal place in the page language.
  - `since` comes from the first down beat after the last up beat. If there is no up beat, it is the oldest beat, prefixed with `≥ `.
  - Down rows are sorted longest-down first.
- Screens:
  - **`ok`:** big green check (SVG), `{up}/{total} OK` in 30 px bold, and a muted line `Verfügbarkeit 24 h: …` / `Uptime 24 h: …`. If `pending > 0`, an extra orange line `1 wird geprüft` / `1 being checked`.
  - **`down`:** alert header, `{n} gestört` / `{n} down` in 34 px red, `{up} von {total} laufen` / `{up} of {total} up`, then rows with a red dot, the name and `seit {since}` / `for {since}`, and `+ {more} weitere` / `+ {more} more`.
  - **`error`:** any exception from either request is caught. The page shows `ui.notice` with `tone="warn"`, "Keine Verbindung zu Uptime Kuma" / "Cannot reach Uptime Kuma" and `Stand HH:MM` / `As of HH:MM`.
  - **`empty`:** a muted notice "Keine Monitore auf der Statusseite" / "No monitors on this status page".

- [ ] **Step 1: Write the failing tests**, with fixtures as dicts in the shape verified above:
  - `test_all_up`: `state == "ok"`, `up == total == 3`, `uptime == "99,9 %"`.
  - `test_two_down_sorted_with_since`: `since` values `"12 min"` and `"3 min"`, longest first.
  - `test_more_than_four_down`: 6 down gives 4 rows and `more == 2`.
  - `test_pending_and_maintenance_not_down`: `state == "ok"`, `pending == 1`, and maintenance counts toward `up`.
  - `test_down_without_up_beat_uses_ge`.
  - `test_unreachable_gives_error_state`: `get_json` raises `requests.ConnectionError`, and the result has `state == "error"` with the message.
  - `test_empty`.
  - `test_time_formats`: both the space format and ISO 8601 parse to the same instant.
  - `test_validate`.
  - `@pytest.mark.browser test_template_renders_ok_and_down`.
- [ ] **Step 2: Run them and verify they fail.**
- [ ] **Step 3: Implement** `page.py` and `template.html` (layout A).
- [ ] **Step 4: Run the tests and verify they pass.** Run the browser test in the image.
- [ ] **Step 5: Docs** `templates/kuma.md` (EN and DE):
  - Install Uptime Kuma with a `docker compose` snippet for `louislam/uptime-kuma:2`, port 3001 and a volume.
  - Add monitors. The recommended way is HTTP(s) monitors on your services' web addresses, which need no rights.
  - Create a status page, add the monitors, note the slug.
  - Add the YAML entry.
  - **Privacy & security:**
    - The status page is readable by anyone who can reach Kuma.
    - Kuma's Docker-container monitor gives *Kuma* access to Docker. If you want it anyway, use a socket proxy with read-only access (for example `tecnativa/docker-socket-proxy` with `CONTAINERS=1` and everything else 0) and never mount the raw socket.
  - Also add the catalog entry, previews `kuma-ok` and `kuma-down`, and the commented example in `config.example.yaml`.
- [ ] **Step 6: Run the whole suite and parity.** All must pass.
- [ ] **Step 7: Commit.** `git commit -m "feat(pages): kuma template (Uptime Kuma status page)"`

---

### Task 7: Template `ai`, provider `claude`, and the status-line scripts

**Files:**
- Create: `pages/ai/page.py`, `pages/ai/providers/__init__.py`, `pages/ai/providers/claude.py`, `pages/ai/template.html`, `pages/ai/README.md`, `pages/ai/test_ai.py`
- Create: `tools/statusline/glancebox-statusline.sh`, `tools/statusline/glancebox-statusline.ps1`
- Create: `server/tests/test_statusline.py`
- Create: `docs/en/templates/ai.md`, `docs/de/templates/ai.md`
- Modify: the catalog, `tools/render_previews.py` (sample `ai-claude`), `config.example.yaml`

**Interfaces:**
- Consumes: `ctx.pushed`, `PUSH_KEYS`, the macros `ui.header`, `ui.bar` and `ui.notice`.
- Produces, in `page.py`:
  - `PUSH_KEYS = {"claude": ("rate_limits",)}`.
  - `PROVIDERS: dict[str, ModuleType]`. Each provider module has `NAME: str` (the header title), `validate(options) -> None` and `fetch(options, ctx) -> dict`.
  - The page's own `validate` checks that `provider` is a known key and delegates to the provider. The page's `fetch` delegates too and adds `title` (option `title`, else `NAME`) and `clock`.
- The template data shape, shared by all providers, is:
  ```
  {"title", "clock", "rows": [{"label", "reset", "percent": float, "text"}],
   "big": None|{"label", "value"}, "stand": "Stand 13:58"|None, "message", "sub"}
  ```
  The template draws `big` (a label and a 30 px bold value) above the rows. Each row shows the label (16 px bold) with `reset` muted on the right, then `ui.bar(percent, text)`. `stand` sits muted and centred below. `message` replaces the body with `ui.notice`.
- Provider `claude` reads `ctx.pushed("claude")`:
  - `None` → `message` "Noch keine Daten" / "No data yet", `sub` "Statuszeilen-Skript einrichten" / "Set up the status-line script".
  - Otherwise the rows come from `rate_limits.five_hour` (label "5 Stunden" / "5 hours") and `rate_limits.seven_day` ("Woche" / "Week"). Each uses `used_percentage` and `resets_at` (epoch seconds). Windows missing from the data are skipped. **Before writing the fixture,** confirm the field names in https://code.claude.com/docs/en/statusline and adjust this plan's names if they differ.
  - `reset`: under 24 h away → `in H:MM`. Otherwise the weekday and time (`Do 09:00` / `Thu 09:00`). `resets_at <= now` → percent 0, text `0 %`, reset `zurückgesetzt` / `reset`.
  - `text` is `f"{round(percent)} %"`. `stand` is `Stand HH:MM` / `As of HH:MM` from `received_at`, always set.
- Status-line script `glancebox-statusline.sh` (POSIX sh, only `curl`):
  - It reads `${XDG_CONFIG_HOME:-$HOME/.config}/glancebox/push.env`, which has the lines `GLANCEBOX_URL=http://…:8080` and `GLANCEBOX_PUSH_KEY=…`. The docs say `chmod 600`.
  - It stores stdin in a variable. If both values are set, it pipes the variable into `curl -s -m 2 -o /dev/null -X POST -H "Authorization: Bearer …" -H "Content-Type: application/json" --data-binary @- "$GLANCEBOX_URL/api/v1/push/claude"` as a background job (`&`, all output to `/dev/null`).
  - If arguments were given, it pipes the same stdin to `"$@"` and exits with that command's status. Otherwise it prints nothing.
  - It never prints errors.
  - The `.ps1` version does the same with `Invoke-RestMethod -TimeoutSec 2` inside `Start-Job`, reading `$env:APPDATA\glancebox\push.env`.

- [ ] **Step 1: Write the failing tests.**
  - In `test_ai.py`:
    - `test_claude_no_data_yet`.
    - `test_claude_rows`: 42 % with 2 h 13 min left gives `reset == "in 2:13"`, and 81 % ending on a Thursday gives `"Do 09:00"`.
    - `test_claude_reset_passed_is_zero`.
    - `test_claude_missing_seven_day_shows_one_row`.
    - `test_validate_unknown_provider`.
    - `test_push_keys_declared`.
    - `@pytest.mark.browser test_template_renders_claude`.
  - In `test_statusline.py` (skipped when `sh` or `curl` is missing), start an `http.server` thread on 127.0.0.1 that records requests, write a temporary `push.env`, then run the script with `XDG_CONFIG_HOME` set:
    - `test_forwards_stdin_with_key`: the server receives the exact stdin JSON at `/api/v1/push/claude` with the Bearer header. Wait up to 3 s, because curl is backgrounded.
    - `test_runs_wrapped_command`: the arguments `sh -c 'cat; echo done'` produce stdout of the stdin plus `done`.
    - `test_fast_when_server_unreachable`: the URL points to a closed port and the script returns within 1 s.
    - `test_silent_without_config`: no `push.env` gives exit 0 and empty stdout.
- [ ] **Step 2: Run them and verify they fail.**
- [ ] **Step 3: Implement** the page, the `claude` provider, the template and both scripts (`chmod +x` the `.sh`).
- [ ] **Step 4: Run the tests and verify they pass.** Run the browser test in the image. Then check by hand: put the script into `~/.claude/settings.json` as `"statusLine": {"type": "command", "command": "/path/glancebox-statusline.sh"}`, run one Claude Code prompt against a local server and see the data on `/preview/<i>.jpg`. Record the result in the task report. **Do not change the user's real `settings.json`.** Use a temporary `CLAUDE_CONFIG_DIR`, or leave this check to the user and say so.
- [ ] **Step 5: Docs** `templates/ai.md` (EN and DE). Cover:
  - An overview of the providers.
  - The Claude setup step by step: `push_key` in `.env`, the page in the YAML with `refresh: 30`, `push.env` on the computer, `settings.json`, wrapping an existing status line by passing its command as arguments, and Windows.
  - Limits: it only updates while Claude Code runs and only at home. The values sit in RAM, so after a restart the page shows "No data yet" until the next answer.
  - Privacy: only `rate_limits` is stored, the rest of the status-line JSON is discarded, and no Anthropic token leaves the computer.
  - Also add the catalog entry, the preview `ai-claude` and the commented example.
- [ ] **Step 6: Run the whole suite and parity.** All must pass.
- [ ] **Step 7: Commit.** `git commit -m "feat(pages): ai template with Claude limits via status-line push"`

---

### Task 8: `ai` providers `anthropic-api`, `openai-api`, `xai-api`

**Files:**
- Create: `pages/ai/providers/anthropic_api.py`, `pages/ai/providers/openai_api.py`, `pages/ai/providers/xai_api.py`
- Modify: `pages/ai/page.py` (register the providers), `pages/ai/test_ai.py`, `docs/*/templates/ai.md`, `tools/render_previews.py` (sample `ai-cost`)

**Interfaces:**
- Consumes: `http.get_json` and the shared data shape from Task 7.
- **Before coding each provider,** read its current official docs and record the exact endpoint, auth header, response fields and pagination in a short comment at the top of the module. Base the fixtures on the documented examples. Expected routes (from the spec research, unverified):
  - Anthropic: `GET https://api.anthropic.com/v1/organizations/cost_report`, or its documented successor, with `x-api-key: <admin key>` and `anthropic-version: 2023-06-01`.
  - OpenAI: `GET https://api.openai.com/v1/organization/costs` with `start_time` set to the month start (unix), `bucket_width=1d` and `Authorization: Bearer <admin key>`. Sum `results[].amount.value` and follow `next_page`.
  - xAI: `GET https://management-api.x.ai/v1/billing/teams/{team_id}/prepaid/balance` with `Authorization: Bearer <management key>`.
- Options:
  - All three take `key` (required; the docs show `${…}`).
  - `anthropic-api` and `openai-api` take an optional `budget` (a positive number in USD).
  - `xai-api` takes `team_id` (required).
- Output:
  - `anthropic-api` and `openai-api`: `big = {"label": "Diesen Monat" / "This month", "value": "18,40 $" / "$18.40"}`. With `budget` there is also a row `{"label": "Budget", "reset": "1.12." / "Dec 1", "percent": spent / budget * 100, "text": "37 %"}`.
  - `xai-api`: `big = {"label": "Guthaben" / "Balance", "value": …}`.
  - Every network or HTTP error is caught and gives `message` "Keine Daten" / "No data" with `sub` `Stand HH:MM` / `As of HH:MM`. The log line must **never** contain the key.
  - Be gentle with the APIs, since cost data changes slowly. `MIN_REFRESH` belongs to the whole page type and has to stay 0, because `claude` needs 30. Each provider therefore keeps a module-level cache keyed by `(provider, sha256(key), team_id)`. It answers from the cache when the last successful result is younger than 300 s (`CACHE_S = 300`).

- [ ] **Step 1: Write the failing tests** for each provider:
  - Month sum over 2 pages of pagination.
  - The budget row at 37 % and at 120 %, which clamps the bar width but keeps the text `120 %`.
  - A 401 gives the `message`, and `caplog` contains no key.
  - `validate` fails on a missing `key` or `team_id`.
  - `test_cached_for_300s`: two fetches 299 s apart make one HTTP call, and a third at 301 s makes a second.
- [ ] **Step 2: Run them and verify they fail.**
- [ ] **Step 3: Implement** the three providers.
- [ ] **Step 4: Run the tests and verify they pass.**
- [ ] **Step 5: Docs.** Add one section per provider to `ai.md` (EN and DE): where to create the key and with which permission.
  - Anthropic must carry a clear warning: the admin key controls the whole organisation, so use a separate organisation or skip this provider.
  - For OpenAI, recommend the narrowest permission the console offers.
  - Add the preview `ai-cost`.
- [ ] **Step 6: Run the whole suite and parity.** All must pass.
- [ ] **Step 7: Commit.** `git commit -m "feat(pages): ai cost providers for Anthropic, OpenAI and xAI APIs"`

---

### Task 9: Provider `copilot`, a gated check

**Files:**
- Either Create: `pages/ai/providers/copilot.py` plus tests and docs, or Modify: the spec (Non-goals) and `ai.md` (a short "not supported, why" line).

- [ ] **Step 1: Research.** Find an **officially documented** HTTP endpoint that returns the Copilot premium-request quota for a personal plan: entitlement, used, remaining and reset date. Also find out which token it accepts and whether a fine-grained PAT with read-only permission works. Candidates are the Copilot SDK's `account.getQuota`, which may hide an official route, and the REST billing endpoint `GET /users/{username}/settings/billing/premium_request/usage`. That one is documented but gives usage only, not the entitlement. `copilot_internal/*` is **not** acceptable, because it is undocumented.
- [ ] **Step 2: Decide.**
  - **If an official route with a read-only token exists,** build it test-first like Task 8. The output is `rows = [{"label": "Premium-Requests", "reset": "1.12.", "percent": used/entitled*100, "text": "212 / 300"}]`, plus `big = {"label": "Übrig" / "Left", "value": "88"}`.
  - **If only usage is available,** combine it with a required option `monthly_allowance` (for example 300), so the user supplies the limit. That is acceptable, because the data stays official.
  - **Otherwise,** do not build the provider. Add the reason to the spec's Non-goals and to `ai.md`.
- [ ] **Step 3: Run the whole suite and parity.** All must pass.
- [ ] **Step 4: Commit.** Either `feat(pages): ai provider copilot` or `docs: copilot quota not available through an official API`.

---

### Task 10: Wrap-up

**Files:**
- Modify: `CHANGELOG.md` (`[Unreleased]`), `README.md` and `README.de.md` (a short "Templates" paragraph near the top with a link to the catalog and the new preview images)

- [ ] **Step 1: Write the changelog entries** under `[Unreleased]` → Added:
  - The `weather`, `kuma` and `ai` templates.
  - `${VAR}` and `.env` support.
  - `push_key` and `POST /api/v1/push/<channel>`.
  - The UI macros and the HTTP helper.
  - The status-line scripts.
  - The template catalog in the docs.
- [ ] **Step 2: Run the full verification:**
  - `cd server && pytest -q -m "not browser" && ruff check . ../pages`
  - `python3 tools/check_docs_parity.py`
  - `docker compose build && docker run --rm glancebox:dev pytest -q -m browser`

  All must pass.
- [ ] **Step 3: Smoke test.** Use a temporary `config.yaml` with `weather` (Frankfurt), `kuma` (pointing at a non-existent host, which should show the orange notice) and `ai` with `provider: claude`, plus `push_key` from `.env`. Run `docker compose up -d`, open `/` and check that all three previews render. Then send a sample `curl` push and check that the Claude page shows bars within 30 s.
- [ ] **Step 4: Commit.** `git commit -m "docs: changelog and README for the template library"`
