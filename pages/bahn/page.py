"""Departure board page (bahn)."""

from __future__ import annotations

MIN_REFRESH = 60  # DB Fahrplan rule: poll at most once a minute


def validate(options: dict) -> None:
    station = options.get("station")
    if not isinstance(station, str) or not station.strip():
        raise ValueError("station is required")
    limit = options.get("limit")
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int)
                              or not 1 <= limit <= 6):
        raise ValueError("limit must be an integer between 1 and 6")


def fetch(options: dict, ctx) -> dict:
    raise NotImplementedError("filled in by the bahn page task")
