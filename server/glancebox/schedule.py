"""Stateless, time-based page selection for the playlist."""

import math
from collections.abc import Sequence

MIN_NEXT_IN = 2
MAX_NEXT_IN = 30


def select(
    durations: Sequence[int], available: Sequence[bool], t: float
) -> tuple[int | None, float]:
    """Return (page index or None, seconds until the current slot ends).

    The slot is derived from ``t mod cycle``. If its page is unavailable, the next
    available page (cyclically) is shown, but the switch time stays that of the slot.
    """
    if not durations or len(durations) != len(available):
        raise ValueError("durations and available must be non-empty and of equal length")
    cycle = sum(durations)
    pos = t % cycle
    slot = 0
    start = 0
    for i, d in enumerate(durations):
        if pos < start + d:
            slot = i
            break
        start += d
    next_in = start + durations[slot] - pos
    n = len(durations)
    for offset in range(n):
        idx = (slot + offset) % n
        if available[idx]:
            return idx, next_in
    return None, next_in


def clamp_next_in(seconds: float) -> int:
    """Round up and clamp to the protocol range of 2-30 seconds."""
    return max(MIN_NEXT_IN, min(MAX_NEXT_IN, math.ceil(seconds)))
