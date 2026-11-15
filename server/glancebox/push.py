"""In-memory inbox for JSON data that clients on the LAN push to the server.

Nothing is written to disk: after a restart the inbox is empty again.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass

CHANNEL_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
MAX_BODY = 65536


@dataclass(frozen=True)
class Pushed:
    data: dict
    received_at: float


class PushInbox:
    """Latest push per channel. The push endpoint is async and runs on the event loop, while
    page ``fetch`` calls read the inbox from worker threads, so access is guarded by a lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, Pushed] = {}

    def put(self, channel: str, data: dict, now: float) -> None:
        with self._lock:
            self._items[channel] = Pushed(dict(data), now)

    def get(self, channel: str) -> Pushed | None:
        with self._lock:
            return self._items.get(channel)
