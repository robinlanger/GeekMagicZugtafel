"""Abfahrten von DBF (db-infoscreen, https://dbf.finalrewind.org) holen."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

USER_AGENT = "zugtafel/1.0 (+https://github.com/; GeekMagic Abfahrtsanzeige)"


@dataclass
class Departure:
    train: str          # z. B. "RB 75" / "S1"
    destination: str
    scheduled: str      # "HH:MM"
    delay: int | None   # Minuten, None = keine Echtzeitdaten
    platform: str | None
    platform_changed: bool
    cancelled: bool

    def realtime(self, now: datetime) -> datetime:
        """Tatsächliche Abfahrt als datetime (Mitternacht wird berücksichtigt)."""
        hour, minute = map(int, self.scheduled.split(":"))
        sched = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Abfahrten kurz nach Mitternacht oder vom Vortag korrekt einordnen.
        if (sched - now) < timedelta(hours=-12):
            sched += timedelta(days=1)
        elif (sched - now) > timedelta(hours=12):
            sched -= timedelta(days=1)
        return sched + timedelta(minutes=self.delay or 0)

    def minutes_until(self, now: datetime) -> int:
        return int((self.realtime(now) - now).total_seconds() // 60)


def _clean_train(train: str) -> str:
    """Kürzt Zugnamen fürs kleine Display.

    "HLB RB75" -> "RB75", "S 1" -> "S1", "RE 60" -> "RE60", "ICE 123" -> "ICE 123"
    """
    parts = train.split()
    if len(parts) < 2:
        return train
    if not parts[-1].isdigit():          # Betreiberpräfix weglassen
        return parts[-1]
    if len(parts[-2]) <= 2:               # S/RB/RE + Nummer zusammenziehen
        return parts[-2] + parts[-1]
    return " ".join(parts[-2:])


def _clean_destination(name: str) -> str:
    """"Frankfurt(Main)Hbf" -> "Frankfurt Hbf", "Bad Soden(Taunus)" -> "Bad Soden"."""
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    return " ".join(name.split())


def parse(payload: dict) -> list[Departure]:
    result: list[Departure] = []
    for item in payload.get("departures", []):
        scheduled = item.get("scheduledDeparture")
        if not scheduled:  # endet hier (nur Ankunft)
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
            )
        )
    return result


def fetch(base_url: str, station: str, *, via: str | None = None,
          platforms: str | None = None, limit: int = 5, timeout: int = 15) -> list[Departure]:
    params = {"version": "3", "limit": str(limit * 3)}  # Puffer, weil Ankünfte rausfallen
    if via:
        params["via"] = via
    if platforms:
        params["platforms"] = platforms
    url = f"{base_url}/{quote(station)}.json"
    resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(f"DBF meldet: {payload['error']}")
    return parse(payload)[:limit]
