"""Discover page types (script pages + built-in ``url``) and validate the playlist."""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
import types as _types
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Sequence
from urllib.parse import urlparse

from .config import AppConfig, ConfigError

PACKAGE = "glancebox_pages"


@dataclass
class PageContext:
    now: datetime
    lang: str
    timezone: str


class PageType:
    def __init__(self, name: str, kind: Literal["script", "url"], *, min_refresh: int = 0,
                 validate: Callable[[dict], None] | None = None,
                 fetch: Callable[[dict, PageContext], dict] | None = None,
                 template_path: Path | None = None) -> None:
        self.name = name
        self.kind = kind
        self.min_refresh = min_refresh
        self._validate = validate
        self._fetch = fetch
        self.template_path = template_path

    def validate(self, options: dict) -> None:
        if self._validate is not None:
            self._validate(options)

    def fetch(self, options: dict, ctx: PageContext) -> dict:
        if self._fetch is None:
            raise NotImplementedError(f"page type {self.name!r} has no fetch()")
        return self._fetch(options, ctx)


def _validate_url_options(options: dict) -> None:
    url = options.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError("url is required")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"url must be an http or https URL, got {url!r}")
    wait_ms = options.get("wait_ms", 0)
    if isinstance(wait_ms, bool) or not isinstance(wait_ms, int) or wait_ms < 0:
        raise ValueError("wait_ms must be an integer >= 0")
    timeout_s = options.get("timeout_s", 15)
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or timeout_s <= 0:
        raise ValueError("timeout_s must be a number > 0")
    wait_for = options.get("wait_for")
    if wait_for is not None and (not isinstance(wait_for, str) or not wait_for):
        raise ValueError("wait_for must be a non-empty CSS selector string")


def _ensure_parent_package() -> None:
    if PACKAGE not in sys.modules:
        parent = _types.ModuleType(PACKAGE)
        parent.__path__ = []  # namespace-like parent; children carry their own search path
        sys.modules[PACKAGE] = parent


def _load_script_page(page_dir: Path) -> PageType:
    name = page_dir.name
    module_name = f"{PACKAGE}.{name}"
    # Drop a previously loaded page of the same name (and its submodules).
    for key in [k for k in sys.modules if k == module_name or k.startswith(module_name + ".")]:
        del sys.modules[key]
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, page_dir / "page.py", submodule_search_locations=[str(page_dir)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:  # any import-time failure of user code
        sys.modules.pop(module_name, None)
        raise ConfigError(f"page {name!r} ({page_dir}): cannot import page.py: "
                          f"{type(e).__name__}: {e}") from e
    fetch = getattr(module, "fetch", None)
    if not callable(fetch):
        raise ConfigError(f"page {name!r} ({page_dir}): page.py must define fetch(options, ctx)")
    validate = getattr(module, "validate", None)
    if validate is not None and not callable(validate):
        raise ConfigError(f"page {name!r} ({page_dir}): validate must be a function")
    min_refresh = getattr(module, "MIN_REFRESH", 0)
    if isinstance(min_refresh, bool) or not isinstance(min_refresh, int) or min_refresh < 0:
        raise ConfigError(f"page {name!r} ({page_dir}): MIN_REFRESH must be an integer >= 0")
    return PageType(name, "script", min_refresh=min_refresh, validate=validate, fetch=fetch,
                    template_path=page_dir / "template.html")


def load_page_types(dirs: Sequence[Path]) -> dict[str, PageType]:
    """Built-in ``url`` plus every ``<dir>/<name>/page.py``; later dirs override earlier ones."""
    _ensure_parent_package()
    result: dict[str, PageType] = {
        "url": PageType("url", "url", validate=_validate_url_options)}
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            raise ConfigError(f"pages directory not found: {d}")
        for page_dir in sorted(p for p in d.iterdir() if p.is_dir()):
            if (page_dir / "page.py").is_file():
                result[page_dir.name] = _load_script_page(page_dir)
    return result


def validate_config(cfg: AppConfig, types: dict[str, PageType]) -> AppConfig:
    """Validate every page against its type; return a config with refresh floors applied."""
    pages = []
    for page in cfg.pages:
        where = f"pages[{page.index}] ({page.type})"
        page_type = types.get(page.type)
        if page_type is None:
            raise ConfigError(f"{where}: unknown page type; available: {', '.join(sorted(types))}")
        try:
            page_type.validate(page.options)
        except ValueError as e:
            raise ConfigError(f"{where}: {e}") from e
        refresh = page.refresh
        if refresh < page_type.min_refresh:
            if page.refresh_explicit:
                raise ConfigError(f"{where}: refresh must be at least {page_type.min_refresh}")
            refresh = page_type.min_refresh
        pages.append(dataclasses.replace(page, refresh=refresh))
    return dataclasses.replace(cfg, pages=tuple(pages))
