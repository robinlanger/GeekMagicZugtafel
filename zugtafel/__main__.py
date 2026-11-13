"""Hauptschleife: Abfahrten holen, rendern, hochladen."""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import departures as dbf
from .config import Config
from .device import GeekMagic
from .render import render

log = logging.getLogger("zugtafel")
_running = True


def _stop(*_):
    global _running
    _running = False


def run_once(cfg: Config, device: GeekMagic | None, tz: ZoneInfo) -> None:
    now = datetime.now(tz)
    title = cfg.title or cfg.station
    try:
        deps = dbf.fetch(cfg.dbf_url, cfg.station, via=cfg.via,
                         platforms=cfg.platforms, limit=cfg.limit, tz=cfg.timezone)
        img = render(title, deps, now, rows=cfg.limit)
        log.info("%d Abfahrten geladen", len(deps))
    except Exception as exc:  # Netzfehler, DBF down, unbekannte Station …
        log.warning("Abfahrten nicht abrufbar: %s", exc)
        img = render(title, None, now, error=f"Stand {now:%H:%M}")

    if cfg.dry_run or device is None:
        img.save(cfg.output)
        log.info("Bild gespeichert: %s", cfg.output)
        return
    try:
        if device.upload(img):
            log.info("Bild hochgeladen")
    except Exception as exc:
        log.warning("Upload auf %s fehlgeschlagen: %s", cfg.device_ip, exc)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = Config.from_env()
    tz = ZoneInfo(cfg.timezone)
    device = None if cfg.dry_run else GeekMagic(cfg.device_ip, cfg.device_profile, cfg.image_name)

    if "--once" in sys.argv:
        run_once(cfg, device, tz)
        return 0

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log.info("Start: %s → %s (alle %ss)", cfg.station, cfg.device_ip or cfg.output, cfg.interval)
    while _running:
        started = time.monotonic()
        run_once(cfg, device, tz)
        if cfg.interval == 60:
            # kurz nach dem Minutenwechsel aktualisieren, damit die Uhr im Header passt
            wait = 62 - (time.time() % 60)
            if time.monotonic() - started + wait < 50:  # DBF: max. 1 Anfrage/Minute
                wait += 60
        else:
            wait = cfg.interval - (time.monotonic() - started)
        wait = max(1.0, wait)
        end = time.monotonic() + wait
        while _running and time.monotonic() < end:
            time.sleep(0.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
