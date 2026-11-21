"""Home Assistant add-on mode.

Active only when the Supervisor runs us: /data/options.json exists and SUPERVISOR_TOKEN is set.
Turns the add-on form into environment variables, writes a starter playlist, and fills in
values Home Assistant already knows (time zone, language, home location, its own API) wherever
the YAML leaves them out. YAML values always win. Secret values are never logged.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

OPTIONS_PATH = Path("/data/options.json")
SUPERVISOR_CORE = "http://supervisor/core"

# Add-on form field -> environment variable the playlist refers to as ${NAME}.
SECRET_FIELDS: dict[str, str] = {
    "push_key": "GLANCEBOX_PUSH_KEY",
    "anthropic_admin_key": "ANTHROPIC_ADMIN_KEY",
    "openai_admin_key": "OPENAI_ADMIN_KEY",
    "xai_management_key": "XAI_MANAGEMENT_KEY",
    "github_copilot_token": "GITHUB_COPILOT_TOKEN",
}
EXTRA_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

STARTER_CONFIG = """\
# Glance Box playlist (Home Assistant add-on).
# Docs: https://robinlanger.github.io/glancebox/
# Time zone, language and location come from Home Assistant unless you set them here
# (timezone:, lang:, and location: on a weather page).
# Secrets go into the add-on's Configuration tab and are used here as ${NAME}.
# Restart the add-on after editing this file.

pages:
  - type: clock
  - type: weather
    refresh: 60
"""


def is_addon(environ: Mapping[str, str], options_path: Path = OPTIONS_PATH) -> bool:
    return bool(environ.get("SUPERVISOR_TOKEN")) and options_path.is_file()


def secrets_env(options: dict, environ: Mapping[str, str]) -> dict[str, str]:
    """Environment variables from the form: fixed fields plus the free list ``extra_secrets``."""
    env: dict[str, str] = {}
    for field, var in SECRET_FIELDS.items():
        value = options.get(field)
        if isinstance(value, str) and value:
            env[var] = value
    reserved = set(SECRET_FIELDS.values())
    for item in options.get("extra_secrets") or []:
        if not isinstance(item, dict):
            continue
        name, value = item.get("name"), item.get("value")
        if not isinstance(name, str) or not EXTRA_NAME_RE.match(name):
            log.warning("extra secret %r ignored: name must be A-Z, 0-9 and _", name)
        elif name in environ or name in reserved:
            log.warning("extra secret %s ignored: this name is already in use", name)
        elif isinstance(value, str) and value:
            env[name] = value
    return env


def ensure_config(path: Path, fallback_dir: Path) -> tuple[Path, bool]:
    """Path of the playlist to load and whether it is the user's file.

    Writes the starter playlist if ``path`` is missing, never overwrites. If ``path`` cannot be
    written, the starter goes to ``fallback_dir`` (not persistent) and the flag is False.
    """
    if path.exists():
        return path, True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(STARTER_CONFIG, encoding="utf-8")
        log.info("wrote starter playlist to %s", path)
        return path, True
    except OSError as e:
        log.warning("cannot write %s (%s); using a temporary starter playlist", path, e)
    fallback_dir.mkdir(parents=True, exist_ok=True)
    fallback = fallback_dir / "config.yaml"
    fallback.write_text(STARTER_CONFIG, encoding="utf-8")
    return fallback, False


@dataclass(frozen=True)
class HaInfo:
    time_zone: str
    language: str | None
    latitude: float
    longitude: float


def lang_from_ha(language: str | None) -> str:
    code = (language or "")[:2].lower()
    return code if code in ("de", "en") else "en"


def ha_defaults(info: HaInfo, environ: Mapping[str, str]) -> Callable[[dict], dict]:
    """Hook for ``load_config``: fill only what the YAML leaves out."""

    def page_defaults(page: object) -> object:
        if not isinstance(page, dict):
            return page
        page = dict(page)
        kind = page.get("type")
        if kind == "weather" and not any(
                page.get(k) is not None for k in ("location", "latitude", "longitude")):
            page["latitude"], page["longitude"] = info.latitude, info.longitude
        elif kind == "homeassistant" and "url" not in page and "token" not in page:
            page["url"] = SUPERVISOR_CORE
            page["token"] = environ.get("SUPERVISOR_TOKEN", "")
        return page

    def hook(data: dict) -> dict:
        out = dict(data)
        out.setdefault("timezone", info.time_zone)
        out.setdefault("lang", lang_from_ha(info.language))
        push_key = environ.get(SECRET_FIELDS["push_key"])
        if push_key and "push_key" not in out:
            out["push_key"] = push_key
        if isinstance(out.get("pages"), list):
            out["pages"] = [page_defaults(p) for p in out["pages"]]
        return out

    return hook
