# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). Firmware and server share one version (`VERSION`).

## [Unreleased]

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
