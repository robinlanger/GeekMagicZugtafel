"""Konfiguration aus Umgebungsvariablen."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    if value is not None:
        value = value.strip()
    return value or default


@dataclass(frozen=True)
class Config:
    station: str
    device_ip: str | None
    device_profile: str
    via: str | None
    platforms: str | None
    limit: int
    interval: int
    dbf_url: str
    title: str | None
    timezone: str
    image_name: str
    dry_run: bool
    output: str

    @classmethod
    def from_env(cls) -> "Config":
        station = _env("STATION")
        if not station:
            raise SystemExit("STATION ist nicht gesetzt (z. B. STATION='Frankfurt(Main)Hbf').")

        dry_run = _env("DRY_RUN", "0").lower() in ("1", "true", "yes", "ja")
        device_ip = _env("DEVICE_IP")
        if not device_ip and not dry_run:
            raise SystemExit("DEVICE_IP ist nicht gesetzt (oder DRY_RUN=1 zum lokalen Testen).")

        profile = (_env("DEVICE_PROFILE", "ultra") or "ultra").lower()
        if profile not in ("ultra", "pro"):
            raise SystemExit("DEVICE_PROFILE muss 'ultra' oder 'pro' sein.")

        # DBF bittet um max. eine Anfrage pro Station und Minute.
        interval = max(60, int(_env("INTERVAL", "60")))

        return cls(
            station=station,
            device_ip=device_ip,
            device_profile=profile,
            via=_env("VIA"),
            platforms=_env("PLATFORMS"),
            limit=max(1, min(6, int(_env("LIMIT", "5")))),
            interval=interval,
            dbf_url=(_env("DBF_URL", "https://dbf.finalrewind.org") or "").rstrip("/"),
            title=_env("TITLE"),
            timezone=_env("TZ", "Europe/Berlin") or "Europe/Berlin",
            image_name=_env("IMAGE_NAME", "zugtafel.jpg") or "zugtafel.jpg",
            dry_run=dry_run,
            output=_env("OUTPUT", "zugtafel.png") or "zugtafel.png",
        )
