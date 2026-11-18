# Projektseite (GitHub Pages) – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a white, Apple-style project site with a guided 5-step setup guide, built from `docs/` with MkDocs Material and deployed to GitHub Pages.

**Architecture:** `mkdocs.yml` at the repo root builds `docs/en` (default, `/`) and `docs/de` (`/de/`) via `mkdocs-static-i18n`. A custom `overrides/home.html` renders the landing page from `index.md` front matter; `docs/stylesheets/extra.css` restyles Material to the mockup. A new `pages.yml` workflow builds with `--strict` and deploys; CI builds on PRs.

**Tech Stack:** Python 3.12, mkdocs, mkdocs-material, mkdocs-static-i18n (exact pins in `requirements-docs.txt`), GitHub Actions (`actions/upload-pages-artifact`, `actions/deploy-pages`), inline SVG illustrations.

**Spec:** `docs/superpowers/specs/2026-11-18-projektseite-design.md`

## Global Constraints

- Site loads nothing from foreign hosts: `theme.font: false`, no repo widget/stars API, no analytics, no CDN.
- Colors: white / `#f5f5f7`, text `#1d1d1f`, secondary `#6e6e73`, accent `#0071e3`, links `#0066cc`; system font stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
- No placeholders ("screenshot follows") on the site; no personal data (example IP `192.168.1.50`, no real LAN IPs, emails, home station in new text).
- `docs/superpowers/**` and `docs/RELEASING.md` are excluded from the site.
- EN default at `/`, DE at `/de/`; every new page exists in both `docs/en` and `docs/de` with the same heading levels; `tools/check_docs_parity.py` stays green.
- Guide paths: `guide/1-get-the-device.md`, `guide/2-flash-the-firmware.md`, `guide/3-set-up-wifi.md`, `guide/4-start-the-server.md`, `guide/5-choose-pages.md` (same file names in both languages).
- `mkdocs build --strict` passes with zero warnings.
- Version in the footer comes from `VERSION` at build time.

## Review Focus

1. Links inside docs that work on GitHub but break on the site (README anchors, `../` paths, `templates/README.md` as index) → `mkdocs build --strict` must pass (Task 1 Step 4, Task 5 Step 2).
2. Language switch on a page lands on the same page in the other language, not the home page → manual check in Task 5 Step 3.
3. Home page on a phone (≤ 400 px): cards and gallery stack, no horizontal scroll → screenshot check in Task 3 Step 4.
4. Dark mode toggle makes the home page unreadable → screenshot check in Task 3 Step 4.
5. Someone edits only the EN `index.md` front matter → parity script fails (Task 2 test).

---

### Task 1: MkDocs skeleton that builds the existing docs

**Files:**
- Create: `mkdocs.yml`, `requirements-docs.txt`, `docs/en/index.md`, `docs/de/index.md` (minimal: title only for now), `docs/stylesheets/extra.css` (empty), `overrides/` (empty dir with `.gitkeep`)
- Modify: `docs/en/setup.md`, `docs/de/setup.md` (README anchor links → `guide/4-start-the-server.md`), `.gitignore` (`site/`)

**Interfaces:**
- Produces: `mkdocs.yml` with `docs_dir: docs`, `custom_dir: overrides`, `extra_css: [stylesheets/extra.css]`, `exclude_docs` for `superpowers/` and `RELEASING.md`, i18n plugin (folder structure, `en` default, `de` with nav translations), `theme.font: false`, palette light default + dark toggle, features `navigation.tabs`, `navigation.footer`, `navigation.instant` off (keeps it simple), `content.code.copy`, `search`.
- Nav (EN titles; DE via plugin `nav_translations`): Guide (5 steps + "After setup": setup, updating, configuration) · Templates (`templates/README.md` as index + each template) · Your own pages (`writing-pages.md`) · Help (recovery, flashing).
- `extra.version` filled by a `hooks:` Python hook `overrides/hooks/version.py` that reads `VERSION` into `config.extra.version`.

- [ ] **Step 1:** Create a venv in the scratchpad, `pip install mkdocs mkdocs-material mkdocs-static-i18n`, then write the exact installed versions into `requirements-docs.txt` (`name==x.y.z`, one per line).
- [ ] **Step 2:** Create the guide files as stubs (heading only) in both languages so nav resolves; they get content in Task 4.
- [ ] **Step 3:** Write `mkdocs.yml` and the version hook as specified above.
- [ ] **Step 4: Verify:** `mkdocs build --strict` → exit 0, no warnings; `grep -rl "fonts.googleapis\|fonts.gstatic\|api.github.com" site/` → no output; `python3 tools/check_docs_parity.py` → OK.
- [ ] **Step 5:** Commit `docs: build the docs with MkDocs Material`.

### Task 2: Parity check compares front-matter keys

**Files:**
- Modify: `tools/check_docs_parity.py`
- Test: `server/tests/test_docs_parity.py`

**Interfaces:**
- Produces: `front_matter_keys(path: Path) -> list[str]` (top-level YAML keys between leading `---` lines, in order; `[]` when absent; plain line parsing `^([A-Za-z_][\w-]*):`, no YAML dependency). `main` reports a mismatch as `front matter keys differ: <en path> vs <de path>` and exits 1.

- [ ] **Step 1: Failing tests** in `server/tests/test_docs_parity.py` (follow its existing tmp-repo helper): `test_front_matter_keys_must_match` (en `index.md` with keys `template, hero_title, lead`, de missing `lead` → exit 1, message contains `front matter keys differ`), `test_front_matter_same_keys_pass` (same keys, different values → exit 0), `test_front_matter_keys_ignores_body` (a `key:` line after the closing `---` is not a key).
- [ ] **Step 2:** `cd server && .venv/bin/pytest -q tests/test_docs_parity.py` → the new tests FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Tests PASS; `python3 tools/check_docs_parity.py` → OK.
- [ ] **Step 5:** Commit `tools: docs parity also compares front-matter keys`.

### Task 3: Landing page (template, texts, styles)

**Files:**
- Create: `overrides/home.html`, `docs/img/site/*.svg` (illustrations used on the landing page, if any)
- Modify: `docs/en/index.md`, `docs/de/index.md`, `docs/stylesheets/extra.css`

**Interfaces:**
- Consumes: `config.extra.version` (Task 1).
- Front-matter keys (identical in both languages): `template: home.html`, `hide: [navigation, toc]`, `kicker`, `title_line1`, `title_line2`, `lead`, `cta_primary`, `cta_secondary`, `steps_title`, `steps_sub`, `steps` (list of 3 × `{title, text, link_text, href}`), `gallery_title`, `gallery_sub`, `gallery` (list of `{img, caption, href}` for bahn, weather, kuma-ok, ai-claude, homeassistant-tiles, clock), `photo_caption`, `features` (list of 3 × `{title, text}`), `footer_license`.
- Copy: EN title "Your display. / Your pages.", DE "Dein Display. / Deine Seiten."; kicker "Open source · no soldering" / "Open Source · ohne Löten"; primary CTA → `guide/1-get-the-device/`, secondary → GitHub repo.
- `home.html` extends `main.html`, overrides `tabs` and `content` blocks; sections exactly as the mockup `landing-white.html`: hero (kicker, h1, lead, two CTAs, `img/hero.jpg`), grey "three steps" cards, template gallery + `img/on-device.jpg` with caption, grey features row, footer line with version + license + links to Releases and `SECURITY.md` on GitHub.
- CSS: all landing classes prefixed `gb-`; Material variables overridden for the white look (`--md-primary-fg-color: #fff`, text colors, accent); header white with hairline border; dark scheme (`[data-md-color-scheme="slate"]`) gets dark surfaces for `gb-` sections. Breakpoints: ≤ 760 px cards and features stack, gallery 2 columns.

- [ ] **Step 1:** Write `index.md` (both languages) and `home.html`, then `extra.css`.
- [ ] **Step 2:** `mkdocs build --strict` → exit 0; parity → OK.
- [ ] **Step 3:** `mkdocs serve`, headless Chrome screenshots of `/` and `/de/` at 1280 and 500 px, light and dark (via the palette toggle's stored preference or `--force-dark-mode` with `media: "(prefers-color-scheme: dark)"` palette entries).
- [ ] **Step 4: Verify** visually against `landing-white.html`: no horizontal scroll at 500 px, readable in dark.
- [ ] **Step 5:** Commit `docs: white landing page for the project site`.

### Task 4: Guided setup (5 steps, EN + DE) with illustrations

**Files:**
- Create: `docs/{en,de}/guide/{1-get-the-device,2-flash-the-firmware,3-set-up-wifi,4-start-the-server,5-choose-pages}.md`, `docs/img/site/stock-update-menu.svg`, `docs/img/site/setup-portal.svg`, `docs/img/site/flow.svg`, `docs/img/site/device-page.png` (+ `device-page-mobile.png`)
- Modify: `docs/stylesheets/extra.css` (guide styles)

**Interfaces:**
- Page pattern (each guide page): `# <Title>`, then a meta line as raw HTML `<p class="gb-meta">Step n of 5 · about x minutes</p>` and `<div class="gb-progress" data-step="n"></div>` (CSS draws 5 segments, first n blue), then `## ` sections, each a numbered sub-step as an ordered list item or `###` with `class="gb-step"`-styled lists, admonitions (`!!! tip`, `!!! warning`) for hints, and a closing nav provided by Material's `navigation.footer`.
- Content sources (shorten, don't copy wholesale; link to the reference page for details): 1 ← README "What you need"/hardware notes; 2 ← `flashing.md` steps 2–4; 3 ← `setup.md` "The setup portal"; 4 ← README quickstart + `configuration.md` "Where the file lives"; 5 ← `templates/README.md`, `setup.md` "The device web page".
- `device-page.png`: render `firmware/web/app.css` with the dev markup (as in `.superpowers/dev/index.html`, IP replaced by `192.168.1.50`, version `0.5.0`) via headless Chrome at 1200 px and 500 px.
- SVG illustrations: flat, white surfaces, 1.5 px `#d2d2d7` strokes, `#0071e3` accent, system font text; stock update menu is generic ("Firmware update", file chooser, "Update" button) without vendor branding; setup portal shows a phone with the `GlanceBox-XXXX` network and the four portal fields.

- [ ] **Step 1:** Write the five EN pages, then the five DE pages with identical heading levels.
- [ ] **Step 2:** Make the illustrations and screenshots; reference them from the pages with alt text.
- [ ] **Step 3: Verify:** `mkdocs build --strict` → exit 0; parity → OK; `grep -rnE "192\.168\.178|gmail|Hamburg|Dieburg" docs/en/guide docs/de/guide docs/en/index.md docs/de/index.md` → no output.
- [ ] **Step 4:** Screenshot one guide page at 1280 and 500 px; compare with the guide mockup.
- [ ] **Step 5:** Commit `docs: guided five-step setup with illustrations`.

### Task 5: Publish (workflow, CI build, README link)

**Files:**
- Create: `.github/workflows/pages.yml`
- Modify: `.github/workflows/ci.yml` (job `docs`: `pip install -r requirements-docs.txt && mkdocs build --strict`), `README.md`, `README.de.md` (link to the site under the badges), `CHANGELOG.md` (Unreleased → Added: project site)

**Interfaces:**
- `pages.yml`: `on: push` to `main` with `paths: [docs/**, overrides/**, mkdocs.yml, requirements-docs.txt, VERSION, README*, .github/workflows/pages.yml]` and `workflow_dispatch`; `permissions: contents: read, pages: write, id-token: write`; `concurrency: pages`; jobs build (checkout, setup-python 3.12 with pip cache on `requirements-docs.txt`, install, `mkdocs build --strict`, `actions/upload-pages-artifact` with `path: site`) and deploy (`environment: github-pages`, `actions/deploy-pages`). Pin action versions like the existing workflows do.

- [ ] **Step 1:** Write the workflow and CI change; README/CHANGELOG lines.
- [ ] **Step 2: Verify:** `mkdocs build --strict` → 0; `python3 tools/check_docs_parity.py` → OK; `server` pytest `-m "not browser"` green; `actionlint` if available, else `python3 -c "import yaml;yaml.safe_load(open('.github/workflows/pages.yml'))"`.
- [ ] **Step 3: Manual:** in `mkdocs serve`, switch language on a guide page and on a template page → lands on the same page in the other language.
- [ ] **Step 4:** Commit `ci: build and publish the project site`; push the branch, open a PR, wait for CI.
- [ ] **Step 5 (after the user's merge OK):** merge; `gh api -X POST repos/robinlanger/glancebox/pages -f build_type=workflow`; run/await `pages.yml`; `gh repo edit --homepage https://robinlanger.github.io/glancebox/`; open the live URL and check `/` and `/de/` load.
