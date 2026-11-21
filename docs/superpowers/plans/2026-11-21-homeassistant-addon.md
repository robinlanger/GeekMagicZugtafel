# Home-Assistant-Add-on Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Glance Box server runs as a Home Assistant add-on: one click to install, a working
clock + weather playlist without any input, secrets in the add-on form, playlist in YAML, overview
in the HA sidebar via Ingress.

**Architecture:** The existing GHCR image is the add-on image (approach A). A new module
`glancebox.addon` detects add-on mode, turns the form (`/data/options.json`) into environment
variables, asks the Supervisor for HA's time zone/language/location and the connect address, writes
a starter playlist, and injects HA defaults into the raw YAML before validation. In add-on mode the
LAN port serves only frames, push and health; a second, Ingress-only server serves the overview.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, requests, PyYAML, pytest; HA add-on `config.yaml`.

**Spec:** `docs/superpowers/specs/2026-11-21-homeassistant-addon-design.md`

## Global Constraints

- Docker installs must behave exactly as before; every add-on code path is gated on add-on mode.
- Add-on mode = `/data/options.json` exists **and** `SUPERVISOR_TOKEN` is set.
- YAML values always win over HA-provided defaults.
- Secrets (form values, `SUPERVISOR_TOKEN`) never appear in logs, error messages or rendered pages.
- No home coordinates are ever written to a file.
- Add-on permissions: `ingress: true`, `ingress_port: 8099`, `panel_icon: mdi:monitor`,
  `panel_admin: true`, `homeassistant_api: true`, `hassio_api: true`, `hassio_role: default`,
  `map: [{type: app_config, read_only: false}]`, `ports: {"8080/tcp": 8090}`, `startup: application`,
  `arch: [amd64, aarch64]`, `init: true`. Nothing else (no host network, docker API, full access).
- Ingress server accepts only `172.30.32.2`; all its URLs relative.
- Add-on `version` == repo `VERSION`.
- Supervisor URLs: `http://supervisor/core/api/config`, `http://supervisor/network/info`,
  `http://supervisor/addons/self/info`; HA page proxy base `http://supervisor/core`.
- Nothing is merged, tagged or announced before the acceptance in Task 8 passes (spec B4).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; no personal IPs or
  e-mail in committed files (use placeholders like `192.168.x.x`).

## Review Focus

1. **HA Core not reachable when the add-on starts** (HA restarting): expect a few retries, then a
   clear log line and exit 1, never a crash with a secret in the traceback. → test in Task 3.
2. **User sets a name in "Weitere Geheimnisse" that already exists** (`PATH`, `SUPERVISOR_TOKEN`,
   a fixed field's variable): expect it is ignored with a warning naming only the variable, not
   the value. → test in Task 2.
3. **`/config` not writable by `pwuser`:** expect the starter playlist still runs (from a temp
   file) and the Ingress page says the file could not be created. → test in Task 2.
4. **Existing `config.yaml` with its own `timezone`, `lang`, weather `location` or HA `url/token`:**
   expect those values untouched. → tests in Task 2.
5. **Host port disabled in the add-on network settings** (`null`) or LAN IP not found: expect the
   connect box to say so instead of showing a broken address. → test in Task 3 and Task 4.

---

### Task 1: `load_config` accepts a defaults hook

**Files:**
- Modify: `server/glancebox/config.py` (`load_config`)
- Test: `server/tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: Path, defaults: Callable[[dict], dict] | None = None) -> AppConfig`.
  `defaults` receives the YAML top-level dict after `expand_env` and before any validation and
  returns the dict to validate.

- [ ] **Step 1: Write the failing tests**

```python
def test_defaults_hook_runs_after_env_and_before_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("K", "x" * 16)
    p = tmp_path / "c.yaml"
    p.write_text("push_key: ${K}\npages:\n  - type: clock\n")
    seen = {}
    def hook(data):
        seen.update(data)
        return {**data, "timezone": "America/New_York", "lang": "en"}
    cfg = load_config(p, defaults=hook)
    assert seen["push_key"] == "x" * 16
    assert (cfg.timezone, cfg.lang) == ("America/New_York", "en")

def test_no_hook_keeps_old_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("pages:\n  - type: clock\n")
    cfg = load_config(p)
    assert (cfg.timezone, cfg.lang) == ("Europe/Berlin", "de")
```

- [ ] **Step 2:** `cd server && pytest tests/test_config.py -q -k "hook"` → FAIL (unexpected keyword).
- [ ] **Step 3:** Add the parameter; call it right after `expand_env`; if it returns a non-dict raise `ConfigError`.
- [ ] **Step 4:** `pytest tests/test_config.py -q` → PASS.
- [ ] **Step 5:** Commit `feat(config): defaults hook for load_config`.

---

### Task 2: `glancebox.addon` — form, starter playlist, HA defaults

**Files:**
- Create: `server/glancebox/addon.py`
- Test: `server/tests/test_addon.py`

**Interfaces:**
- Produces:
  - `OPTIONS_PATH = Path("/data/options.json")`
  - `SECRET_FIELDS: dict[str, str] = {"push_key": "GLANCEBOX_PUSH_KEY", "anthropic_admin_key":
    "ANTHROPIC_ADMIN_KEY", "openai_admin_key": "OPENAI_ADMIN_KEY", "xai_management_key":
    "XAI_MANAGEMENT_KEY", "github_copilot_token": "GITHUB_COPILOT_TOKEN"}` (Task 6 builds the form from it)
  - `EXTRA_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")`
  - `is_addon(environ: Mapping[str, str], options_path: Path = OPTIONS_PATH) -> bool`
  - `secrets_env(options: dict, environ: Mapping[str, str]) -> dict[str, str]` — fixed fields with a
    non-empty value plus `options["extra_secrets"]` (list of `{"name", "value"}`); skips extra names
    that fail `EXTRA_NAME_RE`, already exist in `environ`, or collide with a fixed variable, logging
    `"extra secret %s ignored: ..."` with the name only.
  - `STARTER_CONFIG: str` — comment header (docs link, "time zone, language and location come from
    Home Assistant unless you set them here") plus `pages:` with `- type: clock` and
    `- type: weather` / `refresh: 60`. No coordinates, no timezone/lang keys.
  - `ensure_config(path: Path, fallback_dir: Path) -> tuple[Path, bool]` — returns the path to load
    and whether it is the user's file. Writes `STARTER_CONFIG` if `path` is missing; never
    overwrites; on `OSError` writes it to `fallback_dir / "config.yaml"` and returns `(that, False)`.
  - `@dataclass(frozen=True) class HaInfo: time_zone: str; language: str | None; latitude: float; longitude: float`
  - `lang_from_ha(language: str | None) -> str` — `"de"`/`"en"` from the first two letters, else `"en"`.
  - `ha_defaults(info: HaInfo, environ: Mapping[str, str]) -> Callable[[dict], dict]` — the hook for
    `load_config`; sets only missing keys: `timezone`, `lang`, `push_key` (from
    `GLANCEBOX_PUSH_KEY` when set); for each page `type: weather` without `location`/`latitude`/
    `longitude`: `latitude`, `longitude`; for each `type: homeassistant` without `url` and
    `token`: `url = "http://supervisor/core"`, `token = environ["SUPERVISOR_TOKEN"]`. Returns new
    dicts, never mutates the input.

- [ ] **Step 1: Write the failing tests** (one per bullet, key assertions):

```python
def test_is_addon_needs_both(tmp_path):
    opts = tmp_path / "options.json"; opts.write_text("{}")
    assert is_addon({"SUPERVISOR_TOKEN": "t"}, opts)
    assert not is_addon({}, opts)
    assert not is_addon({"SUPERVISOR_TOKEN": "t"}, tmp_path / "missing.json")

def test_secrets_env_fixed_and_extra(caplog):
    env = secrets_env({"push_key": "p" * 16, "openai_admin_key": "",
                       "extra_secrets": [{"name": "MY_API", "value": "s3cret"},
                                         {"name": "PATH", "value": "evil"},
                                         {"name": "GLANCEBOX_PUSH_KEY", "value": "x"},
                                         {"name": "bad-name", "value": "x"}]},
                      {"PATH": "/usr/bin"})
    assert env == {"GLANCEBOX_PUSH_KEY": "p" * 16, "MY_API": "s3cret"}
    assert "evil" not in caplog.text and "s3cret" not in caplog.text
    assert "PATH" in caplog.text

def test_ensure_config_writes_once(tmp_path):
    p = tmp_path / "config.yaml"
    assert ensure_config(p, tmp_path / "fb") == (p, True)
    assert "type: weather" in p.read_text() and "latitude" not in p.read_text()
    p.write_text("pages:\n  - type: clock\n")
    ensure_config(p, tmp_path / "fb")
    assert p.read_text() == "pages:\n  - type: clock\n"

def test_ensure_config_falls_back_when_not_writable(tmp_path):
    ro = tmp_path / "ro"; ro.mkdir(); ro.chmod(0o500)
    path, own = ensure_config(ro / "config.yaml", tmp_path / "fb")
    assert own is False and path == tmp_path / "fb" / "config.yaml" and path.exists()

def test_ha_defaults_fill_only_missing():
    info = HaInfo("America/New_York", "en-GB", 40.7, -74.0)
    hook = ha_defaults(info, {"SUPERVISOR_TOKEN": "sup", "GLANCEBOX_PUSH_KEY": "k" * 16})
    out = hook({"pages": [{"type": "weather"}, {"type": "weather", "location": "Paris"},
                          {"type": "homeassistant", "entities": ["sensor.a"]},
                          {"type": "homeassistant", "url": "http://other:8123", "token": "t",
                           "entities": ["sensor.a"]}]})
    assert out["timezone"] == "America/New_York" and out["lang"] == "en"
    assert out["push_key"] == "k" * 16
    assert out["pages"][0]["latitude"] == 40.7 and out["pages"][0]["longitude"] == -74.0
    assert "latitude" not in out["pages"][1]
    assert out["pages"][2]["url"] == "http://supervisor/core" and out["pages"][2]["token"] == "sup"
    assert out["pages"][3]["url"] == "http://other:8123"

def test_ha_defaults_yaml_wins():
    hook = ha_defaults(HaInfo("America/New_York", "en", 1.0, 2.0), {"SUPERVISOR_TOKEN": "s"})
    out = hook({"timezone": "Europe/Berlin", "lang": "de", "pages": [{"type": "clock"}]})
    assert (out["timezone"], out["lang"]) == ("Europe/Berlin", "de") and "push_key" not in out

def test_starter_config_validates(tmp_path):
    p = tmp_path / "c.yaml"; p.write_text(STARTER_CONFIG)
    cfg = load_config(p, defaults=ha_defaults(HaInfo("Europe/Berlin", "de", 50.0, 8.0), {"SUPERVISOR_TOKEN": "s"}))
    types = load_page_types(cfg.pages_dirs)
    validate_config(cfg, types)  # no exception
    assert [pg.type for pg in cfg.pages] == ["clock", "weather"]
```

- [ ] **Step 2:** `pytest tests/test_addon.py -q` → FAIL (module missing).
- [ ] **Step 3:** Implement `server/glancebox/addon.py` with the interfaces above.
- [ ] **Step 4:** `pytest tests/test_addon.py tests/test_config.py -q` and `ruff check . ../pages` → PASS.
- [ ] **Step 5:** Commit `feat(addon): options, starter playlist and HA defaults`.

---

### Task 3: Supervisor client

**Files:**
- Modify: `server/glancebox/addon.py`
- Test: `server/tests/test_addon.py`

**Interfaces:**
- Consumes: `HaInfo` (Task 2).
- Produces:
  - `fetch_ha_info(token: str, get: Callable[..., Any] = requests.get, sleep: Callable[[float], None] = time.sleep, attempts: int = 10) -> HaInfo`
    — `GET http://supervisor/core/api/config`, header `Authorization: Bearer <token>`, timeout 5 s;
    retries on connection errors/5xx with 3 s pauses; after the last attempt raises
    `AddonError("Home Assistant API not reachable at startup")` (no token, no response body).
  - `connect_url(token: str, get=requests.get) -> str | None` — LAN IP from
    `GET http://supervisor/network/info` (`interfaces[]` with `primary: true`, first
    `ipv4.address`, strip `/NN`) and host port from `GET http://supervisor/addons/self/info`
    (`data.network["8080/tcp"]`); returns `f"http://{ip}:{port}"`, or `None` if either is missing
    or the call fails. Supervisor answers are wrapped as `{"result": "ok", "data": {...}}`; Core
    `/api/config` is not wrapped.
  - `class AddonError(Exception)`

- [ ] **Step 1: Write the failing tests** with a fake `get` returning objects with `.status_code`,
  `.json()`, `.raise_for_status()`:
  - `test_fetch_ha_info_parses`: config JSON `{"time_zone": "Europe/Berlin", "latitude": 50.1, "longitude": 8.6, "language": "de"}` → `HaInfo("Europe/Berlin", "de", 50.1, 8.6)`; asserts the header `Authorization == "Bearer tok"`.
  - `test_fetch_ha_info_without_language`: missing `language` → `HaInfo(..., language=None, ...)`.
  - `test_fetch_ha_info_retries_then_fails`: `get` raises `requests.ConnectionError` 3 times with `attempts=3` → `AddonError`; `sleep` called 2 times; `"tok"` not in `str(err)`.
  - `test_connect_url`: network/info with two interfaces, the `primary` one `{"ipv4": {"address": ["192.168.1.5/24"]}}`, self/info `{"data": {"network": {"8080/tcp": 8090}}}` → `"http://192.168.1.5:8090"`.
  - `test_connect_url_port_disabled`: `{"8080/tcp": None}` → `None`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run → PASS, ruff clean.
- [ ] **Step 5:** Commit `feat(addon): supervisor client for HA info and connect address`.

---

### Task 4: LAN app without UI, Ingress app with connect box

**Files:**
- Modify: `server/glancebox/app.py`, `server/glancebox/templates/index.html`
- Test: `server/tests/test_app.py`

**Interfaces:**
- Produces:
  - `create_app(..., ui: bool = True)` — with `ui=False` the routes `/` and `/preview/{index}.jpg`
    are not registered (404); frame, push, healthz unchanged.
  - `INGRESS_PEER = "172.30.32.2"`
  - `create_ingress_app(cfg: AppConfig, store: FrameStore, clock: Callable[[], float] = time.time, *, connect: str | None, config_note: str | None) -> FastAPI`
    — serves `/` and `/preview/{index}.jpg` only, no lifespan; a middleware answers 403 for any
    client host other than `INGRESS_PEER`.
  - Template: preview `src="preview/{{ p.index }}.jpg"` (relative, also for the Docker overview);
    when `connect` is given a box "Connect your display" with the address in a `<code>` and a copy
    button (inline JS, `navigator.clipboard`); when `connect` is `None` in add-on mode the box says
    the address could not be determined and to check the add-on's network port; `config_note`
    (e.g. starter file could not be saved) shown under the box. English UI text (like the existing
    overview).

- [ ] **Step 1: Write the failing tests:**
  - `test_ui_false_hides_overview`: `create_app(..., ui=False)` → `GET /` 404, `GET /preview/0.jpg` 404, `GET /api/v1/frame` 200.
  - `test_overview_uses_relative_preview_urls`: Docker `GET /` contains `src="preview/0.jpg"` and not `src="/preview`.
  - `test_ingress_rejects_other_peers`: `TestClient(create_ingress_app(...), client=("192.168.1.9", 5000))` → 403 on `/`.
  - `test_ingress_shows_connect_box`: client `("172.30.32.2", 5000)`, `connect="http://192.168.1.5:8090"` → 200, body contains that address; `/preview/0.jpg` 200.
  - `test_ingress_without_address`: `connect=None` → body contains `"could not be determined"`.
  - `test_ingress_has_no_frame_or_push`: `/api/v1/frame` → 404 on the Ingress app.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement (share the row-building and preview code between both apps). **Step 4:** `pytest tests/test_app.py tests/test_ui.py -q` → PASS.
- [ ] **Step 5:** Commit `feat(app): ingress overview and UI-less LAN app for the add-on`.

---

### Task 5: `serve` wires add-on mode and runs both servers

**Files:**
- Modify: `server/glancebox/__main__.py`
- Test: `server/tests/test_addon.py`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: `addon_setup(environ: MutableMapping[str, str], options_path: Path, config_path: Path, fallback_dir: Path, get=requests.get, sleep=time.sleep) -> AddonSetup`
  with `@dataclass AddonSetup: config_path: Path; defaults: Callable[[dict], dict]; connect: str | None; config_note: str | None`.
  It reads the options, `environ.update(secrets_env(...))`, calls `fetch_ha_info`, `ensure_config`,
  `connect_url`. `_serve`: if `is_addon(os.environ)`, run `addon_setup(os.environ, OPTIONS_PATH,
  Path(args.config), Path("/tmp/glancebox"))`, `load_config(path, defaults=...)`, then run the LAN
  app (`ui=False`, port `args.port`) and the Ingress app (port `args.ingress_port`, default 8099)
  in one event loop (`uvicorn.Server(...).serve()` twice under `asyncio.gather`). `AddonError` and
  `ConfigError` → message on stderr, exit 1. Non-add-on path unchanged.

- [ ] **Step 1: Failing test** `test_addon_setup_end_to_end(tmp_path)`: options file with `push_key`,
  fake `get` serving config/network/self-info, empty config dir → returns a setup whose
  `config_path` exists and is the user's file, `environ["GLANCEBOX_PUSH_KEY"]` set, `connect ==
  "http://192.168.1.5:8090"`, `config_note is None`; `load_config(setup.config_path, defaults=setup.defaults)` yields pages `clock, weather` with the HA coordinates.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run full `pytest -q -m "not browser"` → PASS.
- [ ] **Step 5:** Commit `feat(serve): run as Home Assistant add-on`.

---

### Task 6: Add-on packaging and image labels

**Files:**
- Create: `repository.yaml` (`name: Glance Box`, `url: https://github.com/robinlanger/glancebox`, `maintainer: robinlanger`)
- Create: `ha-addon/config.yaml`, `ha-addon/DOCS.md`, `ha-addon/README.md`, `ha-addon/translations/en.yaml`, `ha-addon/translations/de.yaml`, `ha-addon/icon.png` (128×128), `ha-addon/logo.png` (≈250×100)
- Modify: `Dockerfile` (labels), `.github/workflows/release.yml` (build-arg), `docs/RELEASING.md` (step 1: bump `ha-addon/config.yaml` version too)
- Test: `server/tests/test_addon_package.py`

**Interfaces:**
- Consumes: `SECRET_FIELDS`, `EXTRA_NAME_RE` (Task 2).
- `ha-addon/config.yaml`: `name: Glance Box`, `slug: glancebox`, `version` = `VERSION`,
  `description`, `url`, `image: ghcr.io/robinlanger/glancebox`, the permissions from Global
  Constraints, `ports_description`, `options: {extra_secrets: []}`, `schema`: each
  `SECRET_FIELDS` key as `password?`, `extra_secrets: [{name: "match(^[A-Z][A-Z0-9_]*$)", value: password}]`.
- Dockerfile: `ARG VERSION=dev`, `ARG TARGETARCH`, labels `io.hass.type="app"`,
  `io.hass.version="${VERSION}"`, `io.hass.arch` (`amd64`→`amd64`, `arm64`→`aarch64`; computed in a
  `RUN` writing nothing, or via two build stages — builder's choice as long as the label is right).
- Release workflow passes `build-args: VERSION=${{ env.VERSION }}`.

- [ ] **Step 1: Failing tests:**
  - `test_addon_version_matches`: `yaml.safe_load(ha-addon/config.yaml)["version"] == VERSION.read_text().strip()`.
  - `test_addon_schema_matches_secret_fields`: schema keys minus `extra_secrets` == `set(SECRET_FIELDS)`, each `"password?"`.
  - `test_addon_permissions`: exact values from Global Constraints; keys `host_network`, `docker_api`, `full_access`, `privileged` absent.
  - `test_translations_cover_schema`: both translation files have a `configuration` entry for every schema key.
  - `test_only_one_addon_config`: `git ls-files` shows no other `config.yaml`/`config.json` outside hidden folders (Supervisor would treat it as an add-on).
- [ ] **Step 2:** run → FAIL. **Step 3:** create the files. DOCS.md (shown in the HA store): what it does, "flash the display once in the browser, then everything happens in HA", where `config.yaml` lives (`/addon_configs/<id>_glancebox/` in the File editor), the form fields, that the add-on has **admin access to HA** (needed for the token-free HA page, token stays inside the add-on and is revoked on uninstall), and that port 8090 has no login (LAN only). **Step 4:** `pytest tests/test_addon_package.py -q` and `docker build --build-arg VERSION=$(cat VERSION) -t glancebox:addon-test .` then `docker inspect -f '{{json .Config.Labels}}' glancebox:addon-test` shows the three labels → PASS.
- [ ] **Step 5:** Commit `feat(addon): Home Assistant add-on repository`.

---

### Task 7: Documentation

**Files:**
- Create: `docs/en/home-assistant.md`, `docs/de/home-assistant.md`
- Modify: `mkdocs.yml` (nav under "After setup": `Home Assistant add-on: home-assistant.md`, plus the `nav_translations` entry `Home Assistant add-on: Home-Assistant-Add-on`), `README.md`, `README.de.md` (short section with the `my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Frobinlanger%2Fglancebox` button), `CHANGELOG.md` (`[Unreleased]` → Added)
- Test: existing `tools/check_docs_parity.py` and `mkdocs build --strict`

- [ ] **Step 1:** Write both pages with identical heading structure: requirements (HA OS or
  Supervised, not HA Container), install (button + manual URL), first start (clock + weather from
  HA's home), connect the display ("flash once in the browser, see guide step 3, then enter the
  address from the Glance Box panel"), edit pages, secrets form, HA page without token (admin
  access note), security (LAN port without login, Ingress behind HA login).
- [ ] **Step 2:** `python3 tools/check_docs_parity.py .` → exit 0; `mkdocs build --strict` → no warnings.
- [ ] **Step 3:** Commit `docs: Home Assistant add-on`.

---

### Task 8: Test VM and acceptance (ops, nothing committed except results)

Runs on the home server `ssh server`. No sudo, no host network change, everything under `~/haos`.

- [ ] **Step 1: VM.** Download the current HA OS KVM image (`haos_ova-<ver>.qcow2.xz` from the
  official GitHub releases of `home-assistant/operating-system`, check its SHA-256), run it with
  QEMU/KVM in a Docker container (`--device /dev/kvm`, UEFI, 2 vCPU, 4 GB RAM, user-mode network
  with port forwards host `8123→8123`, `8091→8090` (add-on LAN port), `2222→22222` only if needed),
  `restart: unless-stopped`, compose file in `~/haos`. Expected: `http://<server>:8123` shows HA
  onboarding. Ask the user before choosing other host ports if 8091 or 8123 are taken.
- [ ] **Step 2: Onboarding.** User creates the HA account (their password, not Claude's) and sets
  home location; then installs "Advanced SSH & Web Terminal" or Samba to reach `/addons`.
- [ ] **Step 3: Dev add-on.** Copy the branch into `/addons/glancebox_dev/` with `ha-addon/config.yaml`
  at its root, `image:` removed and `slug: glancebox_dev`, so the Supervisor builds it locally from
  the repo `Dockerfile`. Install and start it.
- [ ] **Step 4: Checks** (each must hold; record results):
  1. Form saves with all fields empty (optional `password?` works); add-on starts; log shows no secret; `/config` writable or the fallback note appears (record which).
  2. Sidebar "Glance Box" opens; connect box shows `http://<VM-LAN-IP>:8090` (note: behind QEMU
     NAT the IP the Supervisor reports is the VM's; the display uses the server's `:8091` forward —
     record both and adjust DOCS.md only if real installs would be affected).
  3. Previews of clock and weather (HA home location, HA time zone).
  4. `curl http://<server>:8091/` → 404; `curl http://<server>:8091/api/v1/frame` → JPEG.
  5. Add a `homeassistant` page without url/token for `sun.sun` → renders a value.
  6. Form: set `push_key`, restart; `curl -X POST` push with that key → 204.
  7. Real display: set server address `http://<server>:8091` in its device page, frames show; after the
     test set it back to the production server and confirm it shows the usual playlist again.
- [ ] **Step 5:** Report results to the user. Only with all checks passed and the user's OK:
  PR, merge, release 0.6.0 per `docs/RELEASING.md`, then a store install from GHCR as final check.
  Remove the VM (`docker compose down`, delete `~/haos`) only when the user says so.
