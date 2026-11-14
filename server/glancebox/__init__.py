"""Glance Box server."""

from pathlib import Path


def _read_version() -> str:
    # VERSION sits at the repo root, two levels above this package (server/glancebox/).
    try:
        return (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip()
    except OSError:
        return "0.0.0+unknown"


__version__ = _read_version()
