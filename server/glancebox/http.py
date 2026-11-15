"""HTTP helper for pages: timeout and User-Agent are always set."""

from typing import Any

import requests

from . import __version__

USER_AGENT = f"glancebox/{__version__} (+https://github.com/robinlanger/glancebox)"


def get_json(url: str, *, params: dict | None = None, headers: dict | None = None,
             timeout: float = 10) -> Any:
    resp = requests.get(url, params=params, timeout=timeout,
                        headers={**(headers or {}), "User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.json()
