# ai-Seite: Claude-Look und Restanzeige – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Version 0.5.1: Option `show: remaining` für die ai-Seite (Issue #6) und ein automatischer Claude-Look (dunkel wie claude.ai) für `provider: claude` und `provider: anthropic-api`.

**Architecture:** `page.fetch` rechnet Zeilen bei `show: remaining` um und hängt den Verbrauch als Stufenwert an; `ui.bar` färbt nach diesem Wert. Provider `claude`/`anthropic-api` melden `theme: "claude"`, worauf `pages/ai/template.html` einen eigenen CSS-Block und die Serifenschrift einbindet. Andere Seiten bleiben unberührt.

**Tech Stack:** Python 3.12, Jinja2, Chromium-Rendering (Playwright), pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-11-19-ai-claude-look-design.md`

## Global Constraints

- Standard bleibt `show: used`; ohne die Option ändert sich kein Wert und kein Pixel bestehender Setups (außer dem Look bei `claude`/`anthropic-api`).
- Farbstufe wird immer aus dem **Verbrauch** berechnet, nie aus dem angezeigten Rest.
- Claude-Farben exakt: Hintergrund `#262624`, Kopf `#1F1E1D` mit 1-px-Linie `#3A3936` unten, Titel `#D97757` in DejaVu Serif Bold, Uhrzeit `#FAF9F5` (DejaVu Sans), Text `#FAF9F5`, Nebentexte `#A8A69C`, Balkenspur `#3A3936`, Balkenradius 6 px, Balken `#D97757`, rot `#E5534B` ab 75 % Verbrauch.
- Kein Logo, keine Anthropic-Bildmarke.
- DejaVu Serif Bold nur in Claude-Seiten einbetten, nicht in `font_face_css()`.
- JPEG ≤ 24576 Bytes (`MAX_JPEG_BYTES`).
- Keine Firmware-Änderung.
- Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; keine persönlichen Daten (IPs, E-Mails) in Commits.
- Tests: `cd server && .venv/bin/pytest -q -m "not browser" ../pages/ai` und `.venv/bin/ruff check . ../pages`. Browser-Tests laufen im Image: `docker build -t glancebox:ci .. && docker run --rm glancebox:ci pytest -q -m browser` (aus `server/`, Kontext = Repo-Wurzel).

## Review Focus

1. Überverbrauch (Copilot/Budget > 100 %) mit `show: remaining` → `0 %`, Balken leer, Stufe rot. Test in Task 1.
2. Claude-Fenster zurückgesetzt (`resets_at` vorbei) mit `remaining` → `100 %`, Stufe nicht rot. Test in Task 1.
3. `anthropic-api` ohne Daten (Fehler) → Claude-Look, aber Kopf rot (`alert`). Test in Task 2.
4. `xai-api` hat keine Zeilen; `show: remaining` darf dort nichts kaputtmachen. Test in Task 1.
5. Andere Seiten/Provider rendern ohne Serif-Font und mit unveränderten Farben (`openai-api` behält Grün). Test in Task 2.

---

### Task 1: Option `show` (used/remaining)

**Files:**
- Modify: `pages/ai/page.py` (validate, fetch)
- Modify: `server/glancebox/templates/ui.html` (`bar`)
- Modify: `pages/ai/template.html:28`
- Test: `pages/ai/test_ai.py`

**Interfaces:**
- Produces: Option `show` ∈ `("used", "remaining")`, Konstante `SHOWS = ("used", "remaining")` in `page.py`. Bei `remaining` hat jede Zeile zusätzlich `"used": float` (Verbrauch in %), `percent = max(0.0, 100 - used)`, `text = f"{round(percent)} %"`. Bei `used` bleiben Zeilen exakt wie bisher (kein `used`-Key).
- Produces: `ui.bar(percent, text, height=30, used=None)` – Stufe aus `used`, falls gesetzt (nicht `none`/undefined), sonst aus `percent`. Template ruft `ui.bar(r.percent, r.text, used=r.used)`.

- [ ] **Step 1: Failing tests** in `test_ai.py`:

```python
def test_validate_show(ai):
    ai.validate({"provider": "claude", "show": "remaining"})
    ai.validate({"provider": "claude", "show": "used"})
    with pytest.raises(ValueError, match="show"):
        ai.validate({"provider": "claude", "show": "left"})


def test_claude_remaining(ai):
    data = ai.fetch({**OPTIONS, "show": "remaining"}, ctx(limits()))
    assert data["rows"] == [
        {"label": "5 Stunden", "reset": "in 2:13", "percent": 58.0, "text": "58 %", "used": 42.0},
        {"label": "Woche", "reset": "Do 09:00", "percent": 19.0, "text": "19 %", "used": 81.0},
    ]


def test_claude_remaining_after_reset_is_full(ai):
    past = (NOW - timedelta(minutes=1)).timestamp()
    row = ai.fetch({**OPTIONS, "show": "remaining"}, ctx(limits(five=(97.0, past))))["rows"][0]
    assert (row["percent"], row["text"], row["used"]) == (100.0, "100 %", 0.0)


def test_copilot_remaining_over_allowance_is_zero(ai, fake_http):
    # reuse the setup of test_copilot_empty_and_over_allowance with usage > allowance
    ...  # assert rows[0]["percent"] == 0.0, rows[0]["text"] == "0 %", rows[0]["used"] > 100


def test_xai_remaining_has_no_rows(ai, fake_http):
    # same fake as test_xai_balance, plus "show": "remaining"
    ...  # assert data["rows"] == [] and data["big"] is not None


def test_bar_level_uses_used_value():
    from glancebox.frames import _jinja_env

    tpl = _jinja_env([PAGES_DIR / "ai"]).get_template("template.html")
    base = dict(title="Claude", clock="14:05", message=None, sub=None, alert=False,
                stand=None, big=None, theme=None)
    low = tpl.render(**base, rows=[{"label": "Woche", "reset": "", "percent": 5.0,
                                    "text": "5 %", "used": 95.0}])
    assert "ui-bad" in low and "width:5.0%" in low
    full = tpl.render(**base, rows=[{"label": "Woche", "reset": "", "percent": 100.0,
                                     "text": "100 %", "used": 0.0}])
    assert "ui-ok" in full
```

Die beiden `...`-Tests nach dem Muster der bestehenden Copilot-/xAI-Tests ausformulieren (gleiche Fakes, nur `show` ergänzt).

- [ ] **Step 2:** `cd server && .venv/bin/pytest -q -m "not browser" ../pages/ai` → die neuen Tests FAIL (unbekannte Option bzw. kein `used`).
- [ ] **Step 3:** `page.validate`: `show` muss in `SHOWS` liegen, sonst `ValueError("show must be 'used' or 'remaining'")`. `page.fetch`: nach dem Provider-Aufruf, wenn `options.get("show") == "remaining"`, jede Zeile ersetzen durch `{**row, "used": row["percent"], "percent": max(0.0, 100.0 - row["percent"]), "text": f"{round(max(0.0, 100.0 - row['percent']))} %"}`.
- [ ] **Step 4:** `ui.bar` um `used=None` erweitern (Stufe: `used` wenn `used is defined and used is not none`, sonst `percent`); Template-Aufruf auf `ui.bar(r.percent, r.text, used=r.used)` umstellen.
- [ ] **Step 5:** Tests erneut → PASS; `.venv/bin/ruff check . ../pages` → sauber. Bestehende Tests (u. a. `test_budget_row_clamps_bar_keeps_text`) bleiben grün.
- [ ] **Step 6: Commit** `feat(ai): show remaining usage instead of used (show: remaining, #6)`

### Task 2: Claude-Look für `claude` und `anthropic-api`

**Files:**
- Create: `server/glancebox/fonts/DejaVuSerif-Bold.ttf` (aus `dejavu-fonts-ttf-2.37` – gleiche Version wie die vorhandenen Dateien; Lizenz `LICENSE-DejaVu.txt` deckt sie ab)
- Modify: `server/glancebox/render.py` (neue Funktion)
- Modify: `server/glancebox/frames.py:94-100` (`_jinja_env`)
- Modify: `pages/ai/page.py` (`EMPTY`), `pages/ai/providers/claude.py`, `pages/ai/providers/anthropic_api.py`
- Modify: `pages/ai/template.html`
- Modify: `tools/render_previews.py` (Sample `ai-claude` mit `"theme": "claude"`)
- Test: `pages/ai/test_ai.py`

**Interfaces:**
- Consumes: `ui.bar(..., used=...)` aus Task 1 (Stufenklassen `ui-ok`/`ui-warn`/`ui-bad`).
- Produces: `render.serif_face_css() -> str` (`@cache`, eine `@font-face`-Regel `font-family:'DejaVu Serif';font-weight:bold`, base64 wie `font_face_css`). In `_jinja_env` als **Funktion** registriert: `env.globals["serif_face_css"] = serif_face_css` (wird nur aufgerufen, wenn das Template sie braucht).
- Produces: Template-Variable `theme` (`None` | `"claude"`); `EMPTY["theme"] = None`. `claude.fetch` setzt `theme: "claude"` in **allen** Rückgabewerten (auch Notices); `anthropic_api.fetch` gibt `{**_cost.show(...), "theme": "claude"}` zurück.

- [ ] **Step 1: Failing tests:**

```python
def test_theme_flag(ai, fake_http):
    assert ai.fetch(OPTIONS, ctx(None))["theme"] == "claude"          # notice too
    assert ai.fetch(OPTIONS, ctx(limits()))["theme"] == "claude"
    fake_http(TWO_PAGES["openai-api"])
    assert ai.fetch(COST["openai-api"], cost_ctx())["theme"] is None


def test_anthropic_no_data_keeps_alert_and_theme(ai, fake_http):
    # fake a 401 as in test_cost_http_401_message_without_key
    ...  # assert data["alert"] is True and data["theme"] == "claude"


def test_claude_theme_html():
    from glancebox.frames import _jinja_env

    tpl = _jinja_env([PAGES_DIR / "ai"]).get_template("template.html")
    base = dict(title="Claude", clock="14:05", message=None, sub=None, alert=False,
                stand="Stand 13:58", big=None,
                rows=[{"label": "Woche", "reset": "", "percent": 42.0, "text": "42 %"}])
    themed = tpl.render(**base, theme="claude")
    assert "'DejaVu Serif'" in themed and "#262624" in themed.upper()
    plain = tpl.render(**base, theme=None)
    assert "DejaVu Serif" not in plain and "#262624" not in plain.upper()
```

Browser-Test (`@pytest.mark.browser`) nach dem Muster von `test_template_renders_claude`: Claude mit 42 % / 95 % gerendert → `has(img, (0x26,0x26,0x24))` (Hintergrund), `has(img, (0xD9,0x77,0x57))` (Balken 42 %), `has(img, (0xE5,0x53,0x4B))` (95 %), **kein** Grün `(60,200,110)`; JPEG-Länge ≤ `MAX_JPEG_BYTES`. Den bestehenden `test_template_renders_claude` (erwartet Grün) entsprechend auf die Claude-Farben umstellen und einen Gegen-Check mit `openai-api`-Budget-Zeile hinzufügen, der weiter Grün zeigt.

- [ ] **Step 2:** Unit-Tests → FAIL (`theme` fehlt).
- [ ] **Step 3:** Font-Datei ablegen (Download `https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2`, Datei `ttf/DejaVuSerif-Bold.ttf`; mit `strings … | grep "Version 2.37"` prüfen). `serif_face_css` in `render.py`, Registrierung in `_jinja_env`.
- [ ] **Step 4:** `theme` in `EMPTY`, `claude.py`, `anthropic_api.py` wie unter Interfaces.
- [ ] **Step 5:** `template.html`: im `head`-Block bei `theme == "claude"` `{{ serif_face_css() | safe }}` plus ein `<style>`, das die Global-Constraint-Farben setzt: `:root`-Variablen (`--bg`, `--header-bg`, `--fg`, `--muted`, `--divider`), `html,body` Hintergrund/Farbe (in `base.html` hart codiert), `.ui-hdr` Unterkante, `.ui-title` Farbe + Serif, `.ui-clock` Farbe, `.ui-bar` Radius 6 px, `.ui-fill.ui-ok` orange, `.ui-fill.ui-warn` und `.ui-fill.ui-bad` rot, `.ui-bar-text` Schatten passend zum neuen Hintergrund. `--header-alert` bleibt, damit `alert` rot bleibt.
- [ ] **Step 6:** Unit-Tests + ruff → PASS. Browser-Tests im Image (Befehl siehe Global Constraints) → PASS.
- [ ] **Step 7:** `tools/render_previews.py`: Sample `ai-claude` bekommt `"theme": "claude"`; Vorschau im Container neu rendern (`docker run --rm -v "$PWD/../docs/img/templates:/out" …` bzw. wie das Skript `OUT` setzt) und `docs/img/templates/ai-claude.png` ansehen (Read) – sieht aus wie Entwurf A.
- [ ] **Step 8: Commit** `feat(ai): Claude look for the claude and anthropic-api providers`

### Task 3: Doku, CHANGELOG, Version 0.5.1

**Files:**
- Modify: `docs/en/templates/ai.md`, `docs/de/templates/ai.md`, `pages/ai/README.md`
- Modify: `CHANGELOG.md`, `VERSION`

- [ ] **Step 1:** Doku (en + de, gleiche Struktur): Optionstabelle um `show` (`used` | `remaining`, Standard `used`) ergänzen; Abschnitt „What it shows“: bei `remaining` zeigt der Balken den Rest, Überverbrauch `0 %`, zurückgesetztes Fenster `100 %`, Farbe richtet sich nach dem Verbrauch; Hinweis, dass `xai-api` keine Balken hat. Ein Satz zum Claude-Look von `claude`/`anthropic-api`. Die Budget-Zeile „Above 100 % the bar stays full …“ gilt nur für `used`. README (Entwickler) um `theme` und `show` ergänzen.
- [ ] **Step 2:** `python3 tools/check_docs_parity.py` → OK.
- [ ] **Step 3:** `VERSION` → `0.5.1`. CHANGELOG: neuen Abschnitt `## [0.5.1]` unter `[Unreleased]` (den vorhandenen Unreleased-Inhalt zur Projekt-Website **mit** in 0.5.1 übernehmen, falls er auf `main` noch unreleased ist), Text: Server-Update, Firmware unverändert (kein OTA nötig); Added: `show: remaining` (#6); Changed: Claude-Look für `claude`/`anthropic-api`. `python3 tools/changelog_section.py 0.5.1 CHANGELOG.md` gibt den Abschnitt aus.
- [ ] **Step 4:** Komplette Suite: `.venv/bin/pytest -q -m "not browser"`, `ruff check . ../pages`, Browser-Tests im Image → alles grün.
- [ ] **Step 5: Commit** `release: 0.5.1` (Body: `Closes #6`).

Danach: superpowers:finishing-a-development-branch (PR gegen `main`; Tag/Release und Deployment auf dem Homeserver erst nach Rückfrage).
