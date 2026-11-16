# Seite `homeassistant` + Simulations-HA – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein simuliertes Home Assistant auf dem Homelab und eine neue Glance-Box-Seite `homeassistant`, die ausgewählte Entitäten als Kacheln oder Liste auf 240x240 zeigt.

**Architecture:** `tools/ha-sim/` enthält eine Compose-Datei und HA-YAML mit Template-Entitäten auf Basis von `now()`. Auf `~/homeassistant-sim` wird es per Kopie ausgerollt. `pages/homeassistant/` folgt dem Muster von `kuma`. `fetch()` macht pro Entität ein `GET /api/states/<id>` über `glancebox.http.get_json` und gibt fertig formatierte Zellen ans Jinja-Template.

**Tech Stack:** Python 3.12, requests, Jinja2, Playwright/Chromium (Renderer), pytest (+ pytest-asyncio), Docker Compose, Home Assistant `ghcr.io/home-assistant/home-assistant:stable`.

**Spec:** `docs/superpowers/specs/2026-11-16-homeassistant-design.md`

## Global Constraints

- Branch `homeassistant`. Committen ja, **nicht pushen, nicht mergen, kein Release, VERSION nicht ändern.**
- Jeder Commit endet mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Keine persönlichen Daten in Code, Doku, Bildern oder Commits: keine E-Mail, keine Heimnetz-IPs (Server-IP, Router-IP), keine echten Gerätenamen. Beispiele: `http://homeassistant.lan:8123`, `192.168.1.x`.
- Der Token steht nur in `.env` (Repo-Wurzel, gitignored), nie in Git, Logs, Fehlermeldungen, Chat oder Bildern.
- Auf `server`: kein sudo. `~/zugtafel` und `~/uptime-kuma` werden nicht verändert und nicht neu gestartet. Lesen ist erlaubt. Display nicht flashen.
- `${NAME}` wird nur als ganzer Wert ersetzt.
- `python3 tools/check_docs_parity.py` bleibt grün, `ruff check . ../pages` (aus `server/`) bleibt grün.
- Tests laufen aus `server/`: `cd server && .venv/bin/pytest …`.
- Texte (exakt):
  - de: `Keine Verbindung zu Home Assistant`, `Token abgelehnt`, `Long-Lived Access Token prüfen`, `Stand`, `fehlt`, `n. v.`, `offen`/`zu`, `erkannt`/`frei`, `an`/`aus`
  - en: `Cannot reach Home Assistant`, `Token rejected`, `Check the long-lived access token`, `As of`, `missing`, `n/a`, `open`/`closed`, `detected`/`clear`, `on`/`off`
- Standardtitel: `Home Assistant`.

## Review Focus

1. **HA liefert eine Zahl als Text mit vielen Stellen oder in Exponentialschreibweise** (`"1.0e-05"`, `"3200.000001"`): Erwartet wird eine sauber gerundete Zahl, kein Absturz und kein langer Text. Test in Task 3 (`test_format_number_rounding_edge_cases`).
2. **`state` ist `"nan"` oder `"inf"`**, wie es manche Integrationen liefern: Das ist keine Zahl, die Zelle zeigt `n. v.` (orange). Test in Task 3.
3. **Die HA-URL endet mit `/`** (`http://ha.lan:8123/`): Es darf kein `//api` entstehen. Test in Task 4 (`test_url_trailing_slash`).
4. **Die Entität existiert, aber `attributes` fehlt oder ist leer**: Dann gilt die Entity-ID als Beschriftung, es gibt keine Einheit und keinen Absturz. Test in Task 4.
5. **Eine Entität im Layout `tiles` mit sehr langem Wert** (`"−10234,5 kWh"` oder ein langer Text-Zustand): Die Schrift wird kleiner, der Wert läuft nicht aus der Kachel. Test in Task 3 (`test_size_class`) und Task 5 (Render prüft, dass die rechte Spalte nicht übermalt wird).

---

### Task 1: Simulations-HA (Dateien + Ausrollen auf `server`)

**Files:**
- Create: `tools/ha-sim/docker-compose.yml`
- Create: `tools/ha-sim/config/configuration.yaml`
- Create: `tools/ha-sim/config/packages/sim.yaml`
- Create: `tools/ha-sim/README.md`

**Interfaces:**
- Produces (für Task 6, Live-Test): Diese Entity-IDs müssen nach dem Start unter `/api/states` existieren:
  `sensor.temperatur_wohnzimmer`, `sensor.luftfeuchte_wohnzimmer`, `sensor.temperatur_aussen`, `sensor.luftfeuchte_aussen`, `sensor.hausverbrauch` (W), `sensor.pv_leistung` (W), `sensor.netz` (W, kann negativ sein), `sensor.energie_heute` (kWh), `sensor.speicher` (%, battery), `sensor.akku_rauchmelder` (%, battery, ~12), `sensor.kellersensor` (°C, zeitweise `unavailable`), `binary_sensor.fenster_bad` (window), `binary_sensor.haustur` (door), `binary_sensor.bewegung_flur` (motion), `light.licht_kuche`, `light.licht_flur`, `switch.kaffeemaschine`.

**Abweichung vom Spec, bewusst (Planer):** Spec §5 nennt den Bind-Mount `./config:/config`. Der Container läuft als root, dann gehören von HA angelegte Dateien root, und ohne sudo kann man sie nicht löschen. Deshalb: der HA-Zustand liegt im benannten Volume `ha-data:/config`, und nur die Repo-Dateien werden einzeln read-only eingehängt (`./config/configuration.yaml:/config/configuration.yaml:ro`, `./config/packages:/config/packages:ro`). Aufräumen geht dann mit `docker compose down -v` ohne sudo. Konto und Token liegen im Volume, also nie im Repo. Eine `.gitignore` in `config/` ist damit überflüssig.

- [ ] **Step 1: Compose-Datei schreiben.** Dienst/`container_name` `homeassistant-sim`, Image `ghcr.io/home-assistant/home-assistant:stable`, `restart: unless-stopped`, `ports: ["8123:8123"]`, `environment: TZ=Europe/Berlin`, die Volumes wie oben, `volumes: ha-data:` top-level. Kein `dns:`, kein `network_mode`, kein `privileged`. Kommentar im Kopf: DNS-Override lokal, wie im README beschrieben.

- [ ] **Step 2: `configuration.yaml` schreiben.** `homeassistant:` mit `name: Sim-Zuhause`, `unit_system: metric`, `time_zone: Europe/Berlin`, `country: DE`, `currency: EUR`, `packages: !include_dir_named packages`. Außerdem `default_config:`, damit Onboarding, Profil/Token und `api` sicher dabei sind.

- [ ] **Step 3: `packages/sim.yaml` schreiben.** Alle Entitäten unter `template:` mit `name:` und `unique_id:`. Der Name ergibt jeweils die oben festgelegte Entity-ID (z. B. Name `Haustür` → `binary_sensor.haustur`, `Licht Küche` → `light.licht_kuche`). Werte aus `now()` mit den Bereichen aus Spec §5:
  - Tageskurven über `now().hour + now().minute/60`, z. B. PV `max(0, 4800 * sin(pi*(h-6)/14))` zwischen 6 und 20 Uhr.
  - Hausverbrauch wechselt minütlich über eine feste Tabelle, die über `now().minute % N` indiziert wird und Werte unter und über 1000 W enthält.
  - `netz` = Hausverbrauch − PV.
  - Fenster Bad `on`, wenn `now().minute % 10 < 3`. Haustür `on`, wenn `now().minute % 15 == 0`. Bewegung `on`, wenn `now().minute % 4 == 0`.
  - Kellersensor mit `availability: "{{ now().minute % 6 != 0 }}"`.
  - Lichter/Schalter als Template-`light`/`switch`, deren Zustand aus einem Minuten- bzw. Abendmuster kommt. `turn_on`/`turn_off` sind leere Aktionen (`[]`), die Simulation braucht kein Schalten.

  Gibt es eine Entität in der aktuellen HA-Version nicht in dieser Form, nimmt der Builder die nächstliegende Template-Variante. Die Entity-ID und das Verhalten bleiben gleich.

- [ ] **Step 4: Lokal validieren.** Run: `docker run --rm -v "$PWD/tools/ha-sim/config:/config" ghcr.io/home-assistant/home-assistant:stable python -m homeassistant --script check_config -c /config`. Expected: keine `Invalid config`-Zeilen. Danach `git status` prüfen: `tools/ha-sim/config/` darf keine neuen, von HA angelegten Dateien enthalten. Sonst diese löschen bzw. eine Kopie im Scratchpad prüfen.

- [ ] **Step 5: README schreiben** (Englisch). Inhalt: Zweck, Kopieren nach `~/homeassistant-sim`, `docker-compose.override.yml` mit `services: homeassistant-sim: dns: [<router-ip>]` und warum, `docker compose up -d`, Onboarding, Token (Profil unten links → Reiter Security → Long-lived access tokens → Create token), Token in `.env` als `HA_URL`/`HA_TOKEN`, Entitätenliste, Aufräumen mit `docker compose down -v`.

- [ ] **Step 6: Ausrollen auf `server`.**
  1. Router-IP aus `~/zugtafel/docker-compose.override.yml` **lesen**.
  2. `ssh server mkdir -p ~/homeassistant-sim`.
  3. `rsync -a tools/ha-sim/ server:homeassistant-sim/`.
  4. `~/homeassistant-sim/docker-compose.override.yml` mit dieser Router-IP per ssh-Heredoc anlegen.
  5. `ssh server 'cd ~/homeassistant-sim && docker compose up -d'`.

  Nur in diesem Verzeichnis arbeiten.

- [ ] **Step 7: Verifizieren.** `ssh server 'docker ps --format "{{.Names}} {{.Status}}"'`: `homeassistant-sim` läuft, `glancebox` und `uptime-kuma` zeigen unveränderte Laufzeit. `curl -s -o /dev/null -w '%{http_code}' http://<server>:8123/api/` liefert `401` (API da, Token nötig). `docker logs homeassistant-sim 2>&1 | grep -i -E "error|invalid"` zeigt keine Fehler zu `sim.yaml`.

- [ ] **Step 8: Commit** `feat(ha-sim): simulated Home Assistant for developing the homeassistant page`.

- [ ] **Step 9: Checkpoint mit dem Maintainer, nicht blockierend.** Ihm sagen: `http://<server>:8123` öffnen, Onboarding durchführen, Token anlegen (Weg wie im README) und in die Repo-Wurzel-`.env` als `HA_URL=http://<server-ip>:8123` und `HA_TOKEN=…` eintragen. Den Token nicht in den Chat schreiben. Weiter mit Task 2. Nach dem Onboarding prüft der Builder mit dem Token aus `.env` (ohne ihn auszugeben), dass alle Entity-IDs aus Interfaces existieren, und korrigiert sonst `sim.yaml` in einem Folge-Commit.

---

### Task 2: Seitentyp anlegen + `validate`

**Files:**
- Create: `pages/homeassistant/page.py`
- Create: `pages/homeassistant/test_homeassistant.py`
- Create: `pages/homeassistant/template.html` (vorerst minimal: `{% extends "base.html" %}`, damit der Seitentyp lädt)

**Interfaces:**
- Produces:
  - `validate(options: dict) -> None`, wirft `ValueError` mit Meldungen wie unten.
  - `entries(options: dict) -> list[Entry]` mit `Entry = NamedTuple("Entry", entity_id: str, label: str | None, decimals: int | None)`.
  - `default_layout(n: int) -> str`, liefert `"tiles"` bei n ≤ 4, sonst `"list"`.
  - Konstanten: `LANGS = ("de", "en")`, `MAX_TILES = 4`, `MAX_LIST = 6`, `ENTITY_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")`, `DEFAULT_TITLE = "Home Assistant"`.

- [ ] **Step 1: Failing tests schreiben**, Fixture `ha` = `load_page_types([PAGES_DIR])["homeassistant"]`, `OPTIONS = {"url": "http://homeassistant.lan:8123", "token": "t0ken", "entities": ["sensor.a"]}`:
  - `test_validate_ok_minimal`: `ha.validate(OPTIONS)` wirft nicht.
  - `test_validate_ok_full`: Entities aus Strings und `{"entity": "sensor.b", "label": "B", "decimals": 2}` gemischt, `layout: "list"`, `lang: "en"`, `title: "X"`.
  - `test_validate_rejects` (parametrisiert, `pytest.raises(ValueError, match=…)`):
    - url fehlt → `url`
    - `url: "ftp://x"` → `http`
    - token fehlt oder `""` → `token`
    - entities fehlt oder `[]` → `entities`
    - 7 Einträge → `at most 6`
    - `"Sensor.A"` → `entity id`
    - `{"label": "x"}` ohne entity → `entity`
    - `decimals: 4` → `decimals`
    - `decimals: True` → `decimals`
    - `label: 5` → `label`
    - `layout: "grid"` → `layout`
    - `layout: "tiles"` mit 5 Einträgen → `at most 4`
    - `lang: "fr"` → `lang`
    - `title: 3` → `title`
  - `test_entries_normalizes`: `[ "sensor.a", {"entity": "sensor.b", "label": "B", "decimals": 0} ]` → `[Entry("sensor.a", None, None), Entry("sensor.b", "B", 0)]`.
  - `test_default_layout`: 1→tiles, 4→tiles, 5→list, 6→list.
  - `test_no_min_refresh`: `ha.min_refresh == 0`.

- [ ] **Step 2: Run** `cd server && .venv/bin/pytest ../pages/homeassistant -q`. Expected: FAIL (Seitentyp fehlt).

- [ ] **Step 3: Implementieren** in `page.py`. Docstring wie bei `kuma`: welche HA-REST-Antwortform angenommen wird (`/api/states/<id>` → `{entity_id, state, attributes, last_changed, last_updated}`, 404 bei unbekannter Entität, 401 bei falschem Token), mit Quelle: HA developer docs, REST API.

- [ ] **Step 4: Run** wie Step 2. Expected: PASS.

- [ ] **Step 5: Commit** `feat(homeassistant): page type with option validation`.

---

### Task 3: Werte formatieren (reine Funktionen)

**Files:**
- Modify: `pages/homeassistant/page.py`
- Test: `pages/homeassistant/test_homeassistant.py`

**Interfaces:**
- Produces:
  - `format_state(state: dict, decimals: int | None, lang: str) -> Cell`
  - `Cell = NamedTuple("Cell", value: str, unit: str | None, tone: str)`, mit `tone` ∈ `""` (weiß), `"warn"` (orange: `n. v.`, `fehlt`), `"open"` (orange), `"on"` (gelb).
  - `state` ist das JSON von `/api/states/<id>`.
  - `size_class(value: str, unit: str | None, layout: str, count: int) -> str`, liefert `"l"`, `"m"` oder `"s"`.

- [ ] **Step 1: Failing tests schreiben.** Hilfsfunktion `st(state, **attrs)` baut `{"entity_id": "sensor.x", "state": state, "attributes": attrs}`.
  - `test_number_with_unit_de_en`: `st("21.37", unit_of_measurement="°C")` → de `Cell("21,4", "°C", "")`, en `Cell("21.4", "°C", "")`.
  - `test_integer_stays_integer`: `st("54", unit_of_measurement="%")` → `"54"`. `st("54.0", …)` → `"54"`.
  - `test_decimals_option`: `st("21.37")` mit decimals=2 → `"21,37"`, mit decimals=0 → `"21"`.
  - `test_watts_to_kilowatts`: `st("3200", unit_of_measurement="W")` → `Cell("3,2", "kW", "")`. `st("999", W)` → `("999", "W")`. `st("-1100", W)` → `("−1,1", "kW")` (U+2212). `st("12500", unit_of_measurement="Wh")` → `("12,5", "kWh")`.
  - `test_negative_uses_minus_sign`: `st("-3.5", unit_of_measurement="°C")` → `"−3,5"`.
  - `test_unavailable_unknown`: `st("unavailable")`, `st("unknown")` → de `Cell("n. v.", None, "warn")`, en `"n/a"`.
  - `test_format_number_rounding_edge_cases`: `"1.0e-05"` → `"0"` (bzw. `"0,0"`, Hauptsache kein `e`), `"3200.000001"` mit W → `"3,2"` kW.
  - `test_nan_inf_are_na`: `"nan"`, `"inf"`, `"-inf"` → `Cell("n. v.", None, "warn")`.
  - `test_binary_words` (parametrisiert über entity_id-Domain, device_class, state → value, tone):
    - `binary_sensor` + `window`/`door`/`opening`/`garage_door`, `on` → `offen`, `"open"`, `off` → `zu`, `""`
    - `motion`/`occupancy`/`presence`, `on` → `erkannt`, `""`, `off` → `frei`
    - `binary_sensor` ohne device_class, `on` → `an`, `""`
    - `light.x`, `on` → `an`, `"on"`, `off` → `aus`
    - `switch.x`, `on` → `an`, `"on"`
    - `input_boolean.x` und `fan.x`, `on` → `an`, `""`
    - en: `open`/`closed`, `detected`/`clear`, `on`/`off`
  - `test_other_text_passthrough`: `st("heat")` bei `climate.x` → `Cell("heat", None, "")`.
  - `test_size_class`: `size_class("21,4", "°C", "tiles", 4) == "l"`, `size_class("−10,4", "kW", "tiles", 4)` ist `"m"` oder `"s"`, `size_class("−10234,5", "kWh", "tiles", 4) == "s"`, `size_class("21,4", "°C", "tiles", 1) == "l"`, `size_class("Langer Zustandstext hier", None, "list", 6) == "s"`.

- [ ] **Step 2: Run** `cd server && .venv/bin/pytest ../pages/homeassistant -q -k "format or number or watts or binary or size or nan or unavailable or decimals or negative or integer or other"`. Expected: FAIL.

- [ ] **Step 3: Implementieren.**
  - Zahl: `float(state)` und `math.isfinite`. Rundung: `decimals`, falls gesetzt. Sonst 0 Stellen, wenn der gerundete Wert ganzzahlig ist (Wert == int), sonst 1 Stelle. Ausgabe ohne Exponent.
  - W/Wh ab |1000| durch 1000 teilen, Einheit kW/kWh.
  - Dezimaltrennzeichen je Sprache, Minus `−`.
  - `size_class` über die Zeichenzahl von Wert + Einheit, mit Grenzen je Layout und Anzahl. Die Schwellen wählt der Builder so, dass „−10,4 kW“ in eine 4er-Kachel passt (wird im Render-Test von Task 5 geprüft). Python statt JavaScript, damit es testbar ist.

- [ ] **Step 4: Run** wie Step 2. Expected: PASS.

- [ ] **Step 5: Commit** `feat(homeassistant): format numbers, units and on/off words`.

---

### Task 4: `fetch` mit Fehlerzuordnung

**Files:**
- Modify: `pages/homeassistant/page.py`
- Test: `pages/homeassistant/test_homeassistant.py`

**Interfaces:**
- Consumes: `entries`, `default_layout`, `format_state`, `size_class` (Tasks 2–3), `glancebox.http.get_json(url, *, params=None, headers=None, timeout=10)`. Der Helper wirft `requests.HTTPError` (mit `.response.status_code`), `requests.ConnectionError`, `requests.Timeout` oder `ValueError` (kaputtes JSON).
- Produces: `fetch(options: dict, ctx) -> dict` mit genau diesen Schlüsseln:
  `{"title": str, "clock": "HH:MM", "lang": "de"|"en", "layout": "tiles"|"list", "state": "ok"|"error"|"token", "items": [{"label": str, "value": str, "unit": str|None, "tone": str, "size": "l"|"m"|"s"}], "message": str|None, "sub": str|None}`.

- [ ] **Step 1: Failing tests schreiben.** Fixture `serve(responses: dict[str, dict | int | Exception])` patcht `glancebox.http.get_json`. Pro aufgerufener URL gilt: ein dict wird zurückgegeben, ein int als `requests.HTTPError` mit einer `requests.Response` mit diesem `status_code` geworfen, eine Exception direkt geworfen. Die Fixture speichert Aufrufe als `(url, headers)`.
  - `test_ok_tiles`: 2 Entitäten → `state == "ok"`, `layout == "tiles"`, Labels aus `friendly_name`, `title == "Home Assistant"`, `clock == "14:05"`.
  - `test_label_option_wins` und `test_label_falls_back_to_entity_id` (ohne `attributes` und mit `attributes: {}`).
  - `test_auth_header_and_urls`: Header `Authorization == "Bearer t0ken"`, URL `http://homeassistant.lan:8123/api/states/sensor.a`.
  - `test_url_trailing_slash`: `url: "http://homeassistant.lan:8123/"` → URL ohne `//api`.
  - `test_missing_entity_404_keeps_others`: eine 404, eine ok → `state == "ok"`. Die fehlende Zelle hat Label = Entity-ID, `value == "fehlt"` bzw. en `"missing"`, `tone == "warn"`. Die andere Zelle ist normal.
  - `test_token_rejected` (parametrisiert 401, 403) → `state == "token"`, `message == "Token abgelehnt"`, `sub == "Long-Lived Access Token prüfen"`, `items == []`. Dasselbe in en.
  - `test_unreachable` (parametrisiert: `requests.ConnectionError("x")`, `requests.Timeout("x")`, `500`, `ValueError("bad json")`) → `state == "error"`, `message == "Keine Verbindung zu Home Assistant"`, `sub == "Stand 14:05"`, `items == []`.
  - `test_error_on_second_entity_drops_first`: Die erste Antwort ist ok, die zweite ConnectionError → `state == "error"` und `items == []`. Keine halben, alten Werte.
  - `test_token_never_logged`: Mit `caplog` auf DEBUG in den Fällen ConnectionError und 401: `"t0ken" not in caplog.text`.
  - `test_layout_default_and_option`: 5 Entitäten → `list`. Option `layout: "list"` bei 2 → `list`.
  - `test_lang_from_ctx`: ohne `lang`-Option, `ctx.lang == "en"` → englische Texte.

- [ ] **Step 2: Run** `cd server && .venv/bin/pytest ../pages/homeassistant -q`. Expected: die neuen Tests scheitern.

- [ ] **Step 3: `fetch` implementieren.** Die Entitäten werden nacheinander abgerufen.
  - 404 → Zelle `fehlt`.
  - 401/403 → sofort `state "token"`.
  - Jede andere Ausnahme → `state "error"`.
  - Geloggt wird wie bei `kuma` als `log.warning("homeassistant: …: %s: %s", type(exc).__name__, exc)`. Die URL darf ins Log, der Header nicht.

- [ ] **Step 4: Run** wie Step 2. Expected: PASS.

- [ ] **Step 5: Commit** `feat(homeassistant): fetch entity states with clear error states`.

---

### Task 5: Template (Kacheln, Liste, Meldungen) + Render-Tests

**Files:**
- Modify: `pages/homeassistant/template.html`
- Test: `pages/homeassistant/test_homeassistant.py`

**Interfaces:**
- Consumes: das dict aus `fetch` (Task 4), `ui.header(title, clock)` und `ui.notice(message, sub, "warn")` aus `server/glancebox/templates/ui.html`, CSS-Variablen aus `base.html`.

- [ ] **Step 1: Failing Render-Test schreiben** `@pytest.mark.browser async def test_template_renders_all_layouts(ha, serve)`, nach dem Muster von `kuma`. Szenarien: tiles mit 1, 2, 3 und 4 Werten, list mit 6 Werten, list mit `fehlt` + `n. v.`, `error`, `token`. Prüfungen:
  - jedes Bild ist 240x240
  - der Kopf bei (120, 4) ist blau (`b > r`)
  - die Fläche hat helle Pixel (`L`-Maximum > 150)
  - Fehler- und Token-Seite haben orange Pixel im Bereich y 100–140 (`r > 200`, `b < 100`)
  - in der 4er-Kachel mit `"−10,4"`/`"kW"` links oben ist der Streifen x 116–124, y 40–110 (Trennlinie/Abstand) frei von hellen Pixeln (`L` < 120). Der Wert läuft also nicht in die rechte Kachel.

- [ ] **Step 2: Run** `cd server && .venv/bin/pytest ../pages/homeassistant -q -m browser`. Expected: FAIL.

- [ ] **Step 3: Template schreiben** nach den Mockups (Spec §6, Layouts):
  - Kopfzeile in jedem Zustand.
  - `tiles` als CSS-Grid mit den Klassen `n1` bis `n4`. Bei 3 Werten ist der erste breit (`grid-column: span 2`).
  - Beschriftung 13 px grau, Wert fett. Größen je `size`: `l` 30 px (bei n1/n2 44 px), `m` 24 px, `s` 18 px.
  - Einheit 15 px grau auf derselben Grundlinie.
  - `list` mit Zeilen von 34 px, links die Beschriftung (15 px, Ellipse), rechts der Wert (17 px fett, `s` 14 px).
  - Töne: `warn`/`open` → `var(--orange)`, `on` → `var(--yellow)`.
  - `error`/`token` → `ui.notice(message, sub, "warn")`.
  - Die Mockup-Vorlage (Scratchpad-Datei aus dem Brainstorming) darf als Ausgangspunkt dienen.

- [ ] **Step 4: Run** wie Step 2, danach die ganze Suite: `cd server && .venv/bin/pytest -q && .venv/bin/ruff check . ../pages`. Expected: alles PASS, ruff ohne Meldungen.

- [ ] **Step 5: Commit** `feat(homeassistant): tiles and list layouts`.

---

### Task 6: Live-Test gegen das Simulations-HA

**Files:**
- Create: `pages/homeassistant/test_live.py`
- Modify: `server/pyproject.toml` (Marker registrieren)

**Interfaces:**
- Consumes: Entity-IDs aus Task 1, `fetch`/`render_page` wie in Task 5. `HA_URL`/`HA_TOKEN` aus `os.environ`, sonst aus `<repo>/.env` (einfacher `NAME=value`-Parser, nur diese zwei Schlüssel).

- [ ] **Step 1: Marker** `homeassistant_live: needs HA_URL and HA_TOKEN of a reachable (simulated) Home Assistant` in `markers` eintragen. Das ganze Modul bekommt `pytestmark = [pytest.mark.homeassistant_live, pytest.mark.skipif(not (URL and TOKEN), reason=…)]`.

- [ ] **Step 2: Tests schreiben:**
  - `test_live_values`: `sensor.temperatur_wohnzimmer`, `sensor.hausverbrauch`, `binary_sensor.fenster_bad`, `light.licht_kuche` → `state == "ok"`. Alle Werte sind weder `fehlt` noch `n. v.` (Ausnahme: kein Kellersensor in der Liste). Die Temperatur hat Einheit `°C`. Das Fenster ist `offen` oder `zu`.
  - `test_live_missing_entity`: `sensor.gibt_es_nicht` → Zelle `fehlt`, die anderen Zellen ok.
  - `test_live_bad_token`: Token `"falsch"` → `state == "token"`.
  - `test_live_unreachable`: dieselbe Host-URL mit Port 1 → `state == "error"`.
  - `test_live_kellersensor`: Wert ist eine Zahl mit °C oder `n. v.`, kein Absturz.
  - `@pytest.mark.browser test_live_render`: `render_page` mit 4 echten Entitäten → 240x240-JPEG.
  - Kein Test gibt `HA_URL` oder `HA_TOKEN` aus. Bei `assert`-Meldungen keine Optionen-Dicts mit Token ausgeben.

- [ ] **Step 3: Ohne `.env` laufen lassen.** `cd server && env -u HA_URL -u HA_TOKEN .venv/bin/pytest ../pages/homeassistant/test_live.py -q` mit vorübergehend umbenannter `.env` oder einem `HA_ENV_FILE`-Override, den der Test dafür anbietet. Expected: alle Tests skipped.

- [ ] **Step 4: Live laufen lassen** (wartet auf Task 1 Step 9, Token in `.env`). `cd server && .venv/bin/pytest ../pages/homeassistant/test_live.py -v`. Expected: alle PASS, nichts skipped. **Erst danach gilt die Seite als getestet.** Wenn der Token noch fehlt: Task 7 vorziehen und hierher zurückkommen.

- [ ] **Step 5: Lokale Sichtprüfung.** Glance Box lokal mit einer Scratchpad-`config.yaml` starten: zwei `homeassistant`-Seiten (tiles: PV/Netz/Haus/Speicher, list: 6 gemischte), `${HA_URL}`/`${HA_TOKEN}` aus `.env`, so wie das Projekt den Server lokal startet (siehe `docs/en/writing-pages.md`). Die Vorschau unter `http://localhost:8080/` als Screenshot anschauen. Der Server bleibt unberührt.

- [ ] **Step 6: Commit** `test(homeassistant): live test against the simulated Home Assistant`.

---

### Task 7: Doku, Vorschaubilder, README

**Files:**
- Create: `docs/en/templates/homeassistant.md`, `docs/de/templates/homeassistant.md`
- Create: `docs/img/templates/homeassistant-tiles.png`, `docs/img/templates/homeassistant-list.png`
- Create: `pages/homeassistant/README.md`
- Modify: `tools/render_previews.py` (SAMPLES)
- Modify: `docs/en/templates/README.md`, `docs/de/templates/README.md` (unter „Server & smart home“)
- Modify: `docs/en/configuration.md`, `docs/de/configuration.md` (Typliste in der `type`-Zeile + Abschnitt „Page type: homeassistant“ nach `kuma`)
- Modify: `config.example.yaml` (auskommentiertes Beispiel nach `kuma`)
- Modify: `CHANGELOG.md` (`## [Unreleased]`)
- Modify: `README.md`, `README.de.md`

- [ ] **Step 1: SAMPLES ergänzen.**
  - `homeassistant-tiles`: Titel `Solar`, en, die 4 Kacheln aus dem Mockup (PV 3.2 kW, Grid −1.1 kW, House 2.1 kW, Battery 78 %).
  - `homeassistant-list`: Titel `Home`, en, 6 Zeilen (Living room 21.4 °C, Outside 8.1 °C, Humidity 54 %, Front door closed, Bathroom window open (orange), Kitchen light on (gelb)).
  - Die `data`-dicts entsprechen dem Format aus Task 4.
  - Run: `server/.venv/bin/python tools/render_previews.py homeassistant-tiles homeassistant-list`. Expected: zwei PNGs. Mit dem Read-Tool ansehen, beide sauber und ohne echte Namen.

- [ ] **Step 2: Vorlagenseite EN + DE** mit derselben Überschriftenfolge wie `kuma.md`: Bilder, What it shows, What you need (mit `### 1. …`-Schritten: Token anlegen, Pfad in der HA-Oberfläche, `.env`), Example, Options (Tabelle aller Optionen aus Spec §6), Setup (`docker compose up -d`, weil sich `.env` ändert), Privacy & security, When something is wrong (jede Meldung: `Cannot reach…`, `Token rejected`, `missing`, `n/a`).
  - Privacy-Text nach Spec §8: Der Token hat die Rechte seines Benutzers, es gibt keine Nur-Lese-Tokens, Empfehlung eigener Benutzer.
  - Der Satz, dass auch Nicht-Admins alles lesen und Dienste aufrufen können, steht **mit Verweis auf die HA-Doku**, nicht als eigene Prüfung. Den Wortlaut gegen die aktuelle HA-Doku prüfen (WebFetch home-assistant.io, Authentication/Users) und die Quelle verlinken.
  - Beispiele mit `http://homeassistant.lan:8123` und `${HA_URL}`/`${HA_TOKEN}`.

- [ ] **Step 3: Katalog, configuration, config.example, CHANGELOG, `pages/homeassistant/README.md`** (kurz, Verweis auf die Vorlagenseite, wie `pages/kuma/README.md`).

- [ ] **Step 4: README.md + README.de.md.**
  - Pitch Zeile 11: `a status page from your Home Assistant` → `live values from your Home Assistant, from solar power to open windows`. DE sinngemäß: `Live-Werte aus deinem Home Assistant, von der Solarleistung bis zum offenen Fenster`.
  - Galerie: eine neue Tabellenzeile `| \`homeassistant\`: tiles | \`homeassistant\`: list | |` mit beiden Bildern und je einer Zeile Text, so gebaut wie die bestehenden Zeilen.
  - Den Satz `The \`url\` page type shows any web page you point it at, for example a status page from Home Assistant.` ersetzen durch `The \`url\` page type shows any web page you point it at.` und dazu den Abgrenzungssatz: `If you want to keep the stock firmware, [geekmagic-hacs](https://github.com/adrienbrault/geekmagic-hacs) is the better fit: a Home Assistant integration that drives the display with its original firmware.` DE sinngemäß gleich.

- [ ] **Step 5: Verifizieren.**
  - `python3 tools/check_docs_parity.py`: Expected: Exit 0.
  - grep nach der E-Mail-Adresse des Maintainers und dem Heimnetz-Präfix `<home-subnet>` (beides bewusst nicht im Repo notiert) über das Repo ohne `.git`: Expected: keine Treffer.
  - `git diff main --stat` auf ungewollte Dateien prüfen.

- [ ] **Step 6: Commit** `docs(homeassistant): template page, catalog, previews and README`.

---

### Task 8: Abschluss

- [ ] **Step 1: Gesamtprüfung.**
  - `cd server && .venv/bin/pytest -q && .venv/bin/ruff check . ../pages`: Expected: PASS, Live-Tests nicht skipped (Token in `.env`).
  - `python3 tools/check_docs_parity.py`: Exit 0.
  - `git log main..homeassistant --format=%B | grep -c "Co-Authored-By: Claude Opus 5.5"` entspricht der Anzahl der Commits.
  - `git log main..homeassistant -p` nach E-Mail-Adresse, `<home-subnet>` und `HA_TOKEN=[^.]` durchsuchen: keine Treffer.
- [ ] **Step 2: Server-Zustand prüfen.** `ssh server 'docker ps --format "{{.Names}} {{.Status}}"'`: `glancebox` und `uptime-kuma` laufen mit Laufzeit vor Arbeitsbeginn, `homeassistant-sim` läuft.
- [ ] **Step 3: Optionaler Test auf dem Display, nur nach ausdrücklicher Rückfrage.**
  - Erst ein Backup von `~/zugtafel/config.yaml` und `.env` anlegen.
  - Den Branch-Code dorthin zu bringen ist ein eigener Schritt und muss mit der Rückfrage geklärt werden.
  - Danach `config.yaml` und `.env` wiederherstellen (die vorherigen Seiten `bahn` + `kuma`) und mit `diff` gegen das Backup belegen.
- [ ] **Step 4: Übergabe** mit dem Skill `superpowers:finishing-a-development-branch`. Nicht pushen, nicht mergen ohne OK.
