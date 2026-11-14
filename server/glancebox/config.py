"""Load and validate the YAML playlist configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_INTERVAL = 30
_TOP_LEVEL_KEYS = {"interval", "timezone", "lang", "pages", "custom_pages_dir"}
_RESERVED_PAGE_KEYS = {"type", "duration", "refresh"}


class ConfigError(Exception):
    """The configuration file is missing, malformed or invalid."""


@dataclass(frozen=True)
class PageConfig:
    index: int
    type: str
    options: dict
    duration: int
    refresh: int
    refresh_explicit: bool = False


@dataclass(frozen=True)
class AppConfig:
    interval: int
    timezone: str
    lang: str
    pages: tuple[PageConfig, ...]
    pages_dirs: tuple[Path, ...]


def _builtin_pages_dir() -> Path:
    env = os.environ.get("GLANCEBOX_PAGES_DIR")
    if env:
        return Path(env)
    # pages/ sits at the repo root, two levels above this package (server/glancebox/).
    return Path(__file__).resolve().parents[2] / "pages"


def _positive_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{where} must be a positive integer, got {value!r}")
    return value


def _parse_page(index: int, raw: Any, interval: int) -> PageConfig:
    where = f"pages[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: must be a mapping")
    page_type = raw.get("type")
    if not isinstance(page_type, str) or not page_type:
        raise ConfigError(f"{where}: missing required key 'type'")
    duration = interval
    if "duration" in raw:
        duration = _positive_int(raw["duration"], f"{where}: duration")
    refresh = duration
    refresh_explicit = "refresh" in raw
    if "refresh" in raw:
        refresh = _positive_int(raw["refresh"], f"{where}: refresh")
    options = {k: v for k, v in raw.items() if k not in _RESERVED_PAGE_KEYS}
    return PageConfig(index, page_type, options, duration, refresh, refresh_explicit)


def load_config(path: Path) -> AppConfig:
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigError(f"{path}: cannot read config: {e}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")

    unknown = sorted(set(data) - _TOP_LEVEL_KEYS, key=str)
    if unknown:
        raise ConfigError(f"{path}: unknown top-level key(s): {', '.join(map(str, unknown))}")

    interval = _positive_int(data.get("interval", DEFAULT_INTERVAL), "interval")
    timezone = data.get("timezone", "Europe/Berlin")
    lang = data.get("lang", "de")
    if not isinstance(timezone, str) or not isinstance(lang, str):
        raise ConfigError("timezone and lang must be strings")

    raw_pages = data.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ConfigError("config needs at least one page under 'pages'")
    pages = tuple(_parse_page(i, p, interval) for i, p in enumerate(raw_pages))

    pages_dirs = [_builtin_pages_dir()]
    custom = data.get("custom_pages_dir")
    if custom is not None:
        if not isinstance(custom, str):
            raise ConfigError("custom_pages_dir must be a string path")
        pages_dirs.append((path.resolve().parent / custom).resolve())

    return AppConfig(interval, timezone, lang, pages, tuple(pages_dirs))
