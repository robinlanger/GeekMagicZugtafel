# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). Firmware and server share one version (`VERSION`).

## [Unreleased]

### Added
- New device web page in an Apple-like look: status tiles (connection, last image, Wi-Fi in
  words, uptime) that refresh every 5 s, grouped settings, light and dark mode, one column on
  phones and two on wide screens. Nothing is loaded from the internet.
- Brightness and night brightness are sliders: the display follows while you drag
  (`POST /api/brightness-preview`, never saved), and the value is saved when you let go.
- Every setting is saved on its own (`POST /api/settings` with any subset of the fields), with a
  check mark or an error message per row; the server address offers Undo. Night mode has a
  switch. The password has its own Change button.
- Firmware upload in the browser computes the MD5 itself and shows a progress bar.

### Security
- Device pages can no longer be framed by other sites (`X-Frame-Options: DENY`,
  `frame-ancestors 'none'`), so the auto-saving controls cannot be clickjacked.
- The embedded CSS/JS are revalidated on every load (`no-cache` + `ETag`) instead of being cached
  for a year, so a script injected once over plain HTTP cannot persist.

### Changed
- The safe-mode page and the message pages use the same look (still no JavaScript in safe mode).
- CSS and JavaScript live in `firmware/web/` and are minified, gzipped and embedded at build time
  (`firmware/scripts/embed_web.py`, `tools/webasset.py`).

### Fixed
- Brightness settings now visibly dim the display. The backlight used a linear duty, so
  20 % looked about half as bright as 100 % and 5 % was only slightly darker. It now follows
  a quadratic curve with a finer PWM range (0 % is still off).

## [0.4.0]

### Added
- `homeassistant` page: live values of up to six Home Assistant entities (REST API with a
  long-lived access token from `.env`) as tiles (1–4) or a list (up to 6). Numbers are rounded,
  W/Wh from 1000 become kW/kWh, on/off becomes words such as `open`/`closed` with colours,
  unavailable entities show `n/a`, unknown ones `missing`. Own notices for no connection and a
  rejected token. Texts in `de` and `en`.
- `tools/ha-sim/`: a simulated Home Assistant (Docker Compose, template entities that change
  over the day) to develop and test the `homeassistant` page without a real smart home.

### Notes
- The firmware code is unchanged from 0.3.0; only its version number changes. This release is
  about the server and its pages.

## [0.3.0]

### Added
- Template library: the `weather` (Open-Meteo forecast), `kuma` (Uptime Kuma status page) and
  `ai` pages. `ai` selects its source with `provider:`: `claude` (5-hour and weekly limits,
  pushed from a Claude Code status line), `anthropic-api`, `openai-api` and `xai-api` (cost or
  balance, optional budget bar) and `copilot` (official GitHub billing usage, needs
  `monthly_allowance`, unit `ai-credits` or `premium-requests`). All pages support `de` and `en`.
- `${VAR}` in `config.yaml` (whole value only, an empty variable is an error) and an optional
  `.env` file that Docker Compose passes to the server, so secrets stay out of the config.
- Top-level `push_key` and `POST /api/v1/push/<channel>`: a key-protected inbox on the home
  network that pages use to receive data. It answers 404 without `push_key`.
- Shared UI macros (`ui.html`) for the page templates and the `glancebox.http.get_json` helper
  with timeout and `glancebox/<version>` User-Agent.
- Status-line scripts for Claude Code in `tools/statusline/` (shell and PowerShell) that push
  the rate limits to the server.
- Template catalog in the docs (`docs/en/templates/`, `docs/de/templates/`) with preview images
  in `docs/img/templates/`; the EN/DE docs parity check now covers subfolders.

## [0.2.0]

### Added
- Night mode: on the device web page set a nightly window (for example 22:00–07:00, may span
  midnight) and a night brightness from 0 to 100 %; 0 % turns the backlight off. `/status`
  reports `local_time` and `night`.
- Server: every frame response carries `X-Local-Time: HH:MM:SS` in the configured `timezone`;
  the display uses it as its clock. Night mode needs both firmware and server 0.2.0.

### Fixed
- The backlight is now fully dark while the display initialises (it was at 5 %).

## [0.1.0]

First release of Glance Box: a Docker server that renders pages to 240x240 JPEG frames and
firmware for the GeekMagic SmallTV Ultra (ESP8266) that shows them.

### Added
- Server (multi-arch image, amd64 and arm64, runs as non-root on port 8080): playlist of pages
  with per-page `duration` and `refresh`, headless rendering to baseline JPEG (240x240, at most
  24 576 bytes), frame endpoint `GET /api/v1/frame` with `ETag`/`304` and a clamped `X-Next-In`,
  last-good-frame fallback (600 s) and an error frame instead of a black screen.
- Built-in `bahn` page that respects the 60 s minimum refresh.
- Built-in `clock` page; host port of the Docker setup configurable with `GLANCEBOX_PORT` in `.env`.
- Firmware: Wi-Fi setup portal (`GlanceBox-XXXX` access point), stream-decoded JPEG frame loop,
  offline status screen after 120 s without a frame, DE/EN device web UI with `/status`.
- OTA updates over HTTP with Basic auth and a mandatory MD5; a wrong checksum or a bad image is
  rejected and the running image stays untouched.
- Boot-loop protection: boot counter in RTC memory, safe mode after 3 failed boots.
- Release pipeline (firmware `.bin` with `.md5`/`.sha256`, GHCR image, GitHub release) and the
  on-hardware OTA smoketest (`tools/ota-smoketest.sh`).
