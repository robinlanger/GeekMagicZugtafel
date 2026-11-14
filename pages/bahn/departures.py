"""Fetch departures from DBF (db-infoscreen, https://dbf.finalrewind.org)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

from glancebox import __version__

USER_AGENT = f"glancebox/{__version__} (+https://github.com/robinlanger/glancebox)"


@dataclass
class Departure:
    train: str          # e.g. "RB 75" / "S1"
    destination: str
    scheduled: str      # "HH:MM"
    delay: int | None   # minutes, None = no realtime data
    platform: str | None
    platform_changed: bool
    cancelled: bool
    next_stops: list[str] = field(default_factory=list)  # destination + stops after the station

    def realtime(self, now: datetime) -> datetime:
        """Actual departure as a datetime (midnight rollover is handled)."""
        hour, minute = map(int, self.scheduled.split(":"))
        sched = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Place departures just after midnight or from the previous day correctly.
        if (sched - now) < timedelta(hours=-12):
            sched += timedelta(days=1)
        elif (sched - now) > timedelta(hours=12):
            sched -= timedelta(days=1)
        return sched + timedelta(minutes=self.delay or 0)

    def minutes_until(self, now: datetime) -> int:
        return int((self.realtime(now) - now).total_seconds() // 60)


def _clean_train(train: str) -> str:
    """Shorten train names for the small display.

    "HLB RB75" -> "RB75", "S 1" -> "S1", "RE 60" -> "RE60", "ICE 123" -> "ICE 123"
    """
    parts = train.split()
    if len(parts) < 2:
        return train
    if not parts[-1].isdigit():          # drop the operator prefix
        return parts[-1]
    if len(parts[-2]) <= 2:               # join S/RB/RE with the number
        return parts[-2] + parts[-1]
    return " ".join(parts[-2:])


def _clean_destination(name: str) -> str:
    """"Frankfurt(Main)Hbf" -> "Frankfurt Hbf", "Bad Soden(Taunus)" -> "Bad Soden"."""
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    return " ".join(name.split())


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]", "", name.lower())


def _next_stops(item: dict, station: str | None) -> list[str]:
    """Stops AFTER our own station (the route also contains the stops before it)."""
    route = [r.get("name", "") for r in item.get("route") or []]
    if station:
        key = _norm(station)
        for i, name in enumerate(route):
            if _norm(name) == key:
                return route[i + 1:]
    # Station not found in the route (e.g. an EVA number was given):
    # then only the destination is used for filtering.
    return []


def parse(payload: dict, station: str | None = None) -> list[Departure]:
    result: list[Departure] = []
    for item in payload.get("departures", []):
        scheduled = item.get("scheduledDeparture")
        if not scheduled:  # terminates here (arrival only)
            continue
        platform = item.get("platform")
        result.append(
            Departure(
                train=_clean_train(item.get("train") or "?"),
                destination=_clean_destination(item.get("destination") or ""),
                scheduled=scheduled,
                delay=item.get("delayDeparture"),
                platform=platform,
                platform_changed=bool(platform and platform != item.get("scheduledPlatform")),
                cancelled=bool(item.get("isCancelled")),
                next_stops=[item.get("destination") or "", *_next_stops(item, station)],
            )
        )
    return result


def parse_directions(value: str | None) -> list[str]:
    """"Wiesbaden, Frankfurt" -> ["wiesbaden", "frankfurt"]"""
    return [_norm(v) for v in (value or "").split(",") if _norm(v)]


def matches(dep: Departure, directions: list[str]) -> bool:
    """True if the train calls at one of the places after our own station."""
    if not directions:
        return True
    stops = [_norm(s) for s in dep.next_stops]
    return any(d in s for d in directions for s in stops)


def fetch(base_url: str, station: str, *, via: str | None = None,
          platforms: str | None = None, limit: int = 5, timeout: int = 15,
          tz: str = "Europe/Berlin", user_agent: str = USER_AGENT) -> list[Departure]:
    directions = parse_directions(via)
    # Over-fetch, because arrivals and filtered directions drop out
    params = {"version": "3", "limit": str(limit * (5 if directions else 3))}
    if platforms:
        params["platforms"] = platforms
    url = f"{base_url}/{quote(station)}.json"
    resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": user_agent})
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(f"DBF reported: {payload['error']}")
    deps = [d for d in parse(payload, station) if matches(d, directions)]
    # Sort by actual departure (DBF sorts by scheduled time)
    now = datetime.now(ZoneInfo(tz))
    deps.sort(key=lambda d: d.realtime(now))
    return deps[:limit]
