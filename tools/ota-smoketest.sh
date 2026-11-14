#!/usr/bin/env bash
# OTA smoketest for a real Glance Box device (spec 5.4 point 4). See docs/RELEASING.md.
#
# Usage: GB_PASSWORD=<pw> tools/ota-smoketest.sh [--skip-frames] <device-ip> <new.bin> <previous.bin>
#
#   1. read the running version from /status
#   2. upload <new.bin> with a wrong MD5: expect HTTP 400, same version, no reboot
#   3. upload <new.bin>: wait for the reboot, version matches, boot_failed == 0, frames_ok grows
#   4. upload <previous.bin>: same checks
#   5. upload <new.bin> again: same checks
#
# --skip-frames skips the frames_ok check (device has no server configured yet).
# The device's OTA user is always "admin". Needs only bash, curl, jq, strings.
# Prints "PASS" and exits 0, or "FAIL <step>" and exits 1. Never prompts.
set -euo pipefail

REBOOT_TIMEOUT=90   # seconds until the new version answers on /status
HEALTHY_TIMEOUT=90  # seconds after that until boot_failed is back to 0
FRAMES_TIMEOUT=60   # seconds until frames_ok increases
CURL_TIMEOUT=10     # per ordinary request
UPLOAD_TIMEOUT=120  # per upload

skip_frames=0
args=()
for a in "$@"; do
  case "$a" in
    --skip-frames) skip_frames=1 ;;
    -h | --help) sed -n '2,15p' "$0"; exit 0 ;;
    *) args+=("$a") ;;
  esac
done
if [ "${#args[@]}" -ne 3 ]; then
  echo "usage: GB_PASSWORD=<pw> $0 [--skip-frames] <device-ip> <new.bin> <previous.bin>" >&2
  exit 2
fi
ip=${args[0]}
new_bin=${args[1]}
prev_bin=${args[2]}
: "${GB_PASSWORD:?set GB_PASSWORD to the device OTA password}"
for f in "$new_bin" "$prev_bin"; do
  [ -f "$f" ] || { echo "no such file: $f" >&2; exit 2; }
done
for tool in curl jq strings; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 2; }
done
base="http://$ip"

step=init
fail() {
  echo "FAIL $step: $*" >&2
  echo "FAIL $step"
  exit 1
}
log() { echo "[$step] $*" >&2; }

# MD5 of a file as 32 hex chars (md5sum on Linux, md5 -q on macOS).
md5_of() {
  if command -v md5sum >/dev/null; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi
}

# Version embedded in a .bin as the literal GBVER:<version> (exactly once).
bin_version() {
  local tags
  tags=$(strings -a "$1" | grep -o 'GBVER:[0-9A-Za-z._+-]*' | sort -u || true)
  if [ "$(printf '%s\n' "$tags" | grep -c .)" -ne 1 ]; then
    echo "$1 has no unique GBVER tag (found: ${tags:-none})" >&2
    return 1
  fi
  echo "${tags#GBVER:}"
}

# GET /status into $status_json; returns non-zero if the device does not answer sensibly.
status_json=
get_status() {
  status_json=$(curl -sf --max-time "$CURL_TIMEOUT" "$base/status") || return 1
  jq -e 'has("version") and has("uptime_s")' <<<"$status_json" >/dev/null 2>&1 || return 1
}
field() { jq -r ".$1" <<<"$status_json"; }

# POST /update. Args: file md5. Prints the HTTP status code (000 if curl failed).
# The md5 form field must precede the file part. Credentials go through a config file
# on a pipe so the password never shows up in the process list.
upload() {
  local pw=${GB_PASSWORD//\\/\\\\}
  pw=${pw//\"/\\\"}
  curl -s -o /dev/null -w '%{http_code}' --max-time "$UPLOAD_TIMEOUT" \
    --config <(printf 'user = "admin:%s"\n' "$pw") \
    -F "md5=$2" -F "firmware=@$1" "$base/update" || true
}

# After a committed upload: wait for the reboot, then for the expected version.
# Phase A: the device goes away or its uptime drops. Phase B: /status shows the version.
await_reboot() {
  local expected=$1 pre_version=$2 pre_uptime=$3 deadline last=$3 up
  deadline=$((SECONDS + 30))
  while :; do
    if ! get_status; then break; fi
    up=$(field uptime_s)
    if [ "$up" -lt "$last" ] || [ "$(field version)" != "$pre_version" ]; then break; fi
    last=$up
    [ "$SECONDS" -lt "$deadline" ] || fail "device did not reboot after upload (uptime $pre_uptime s -> $last s)"
    sleep 1
  done
  deadline=$((SECONDS + REBOOT_TIMEOUT))
  until get_status && [ "$(field version)" = "$expected" ]; do
    [ "$SECONDS" -lt "$deadline" ] || fail "version $expected not seen within ${REBOOT_TIMEOUT}s (last: ${status_json:-no answer})"
    sleep 2
  done
}

# Flash <bin> (expecting <version>) and verify the new image is healthy.
flash_and_verify() {
  local bin=$1 expected=$2 md5 code pre_version pre_uptime frames0 deadline
  get_status || fail "device not reachable at $base"
  pre_version=$(field version)
  pre_uptime=$(field uptime_s)
  md5=$(md5_of "$bin")
  log "uploading $bin (version $expected, md5 $md5)"
  code=$(upload "$bin" "$md5")
  [ "$code" = "200" ] || fail "upload returned HTTP $code, expected 200"
  await_reboot "$expected" "$pre_version" "$pre_uptime"
  log "version $expected is up"

  frames0=$(field frames_ok)
  deadline=$((SECONDS + HEALTHY_TIMEOUT))
  until get_status && [ "$(field boot_failed)" = "0" ]; do
    [ "$SECONDS" -lt "$deadline" ] || fail "boot_failed still not 0 after ${HEALTHY_TIMEOUT}s (${status_json:-no answer})"
    sleep 3
  done
  [ "$(field version)" = "$expected" ] || fail "version changed to $(field version) while waiting"
  [ "$(field safe_mode)" = "false" ] || fail "device is in safe mode"
  log "boot_failed == 0, not in safe mode"

  if [ "$skip_frames" -eq 1 ]; then
    log "frames_ok check skipped (--skip-frames)"
    return 0
  fi
  deadline=$((SECONDS + FRAMES_TIMEOUT))
  until get_status && [ "$(field frames_ok)" -gt "$frames0" ]; do
    [ "$SECONDS" -lt "$deadline" ] || fail "frames_ok did not increase within ${FRAMES_TIMEOUT}s (stayed at $frames0; use --skip-frames if no server is configured)"
    sleep 3
  done
  log "frames_ok $frames0 -> $(field frames_ok)"
}

step="1 read version"
new_version=$(bin_version "$new_bin") || fail "cannot read version from $new_bin"
prev_version=$(bin_version "$prev_bin") || fail "cannot read version from $prev_bin"
[ "$new_version" != "$prev_version" ] || fail "new and previous bins both report version $new_version; reboots could not be told apart"
get_status || fail "device not reachable at $base"
start_version=$(field version)
log "device runs $start_version; new=$new_version previous=$prev_version"

step="2 wrong md5 rejected"
uptime_before=$(field uptime_s)
code=$(upload "$new_bin" "00000000000000000000000000000000")
[ "$code" = "400" ] || fail "wrong md5 returned HTTP $code, expected 400"
get_status || fail "device not reachable after rejected upload"
[ "$(field version)" = "$start_version" ] || fail "version changed to $(field version)"
[ "$(field uptime_s)" -ge "$uptime_before" ] || fail "device rebooted after rejected upload"
log "HTTP 400, still running $start_version"

step="3 flash new"
flash_and_verify "$new_bin" "$new_version"
step="4 flash previous"
flash_and_verify "$prev_bin" "$prev_version"
step="5 flash new again"
flash_and_verify "$new_bin" "$new_version"

echo "PASS"
