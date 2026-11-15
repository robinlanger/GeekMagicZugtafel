"""Provider claude: Claude plan limits (5 hours, week), pushed by the Claude Code status line.

Field names verified against https://code.claude.com/docs/en/statusline (2026-11-15):
- rate_limits.five_hour.used_percentage, rate_limits.seven_day.used_percentage:
  percentage of the window used, 0 to 100 (a float, e.g. 23.5).
- rate_limits.five_hour.resets_at, rate_limits.seven_day.resets_at: Unix epoch seconds.
- rate_limits is present only for claude.ai Pro/Max/Ultra plans and only after the first API
  response of a session; each window may be absent on its own, and Claude Code drops a window
  once its resets_at has passed. (rate_limits.spend_limit exists behind a gateway; not shown.)

tools/statusline/glancebox-statusline.sh posts that JSON to /api/v1/push/claude; the server
keeps only `rate_limits` (PUSH_KEYS in page.py).
"""

from __future__ import annotations

from datetime import datetime

NAME = "Claude"
CHANNEL = "claude"

WINDOWS = (("five_hour", {"de": "5 Stunden", "en": "5 hours"}),
           ("seven_day", {"de": "Woche", "en": "Week"}))
WEEKDAYS = {"de": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
            "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}
TEXT = {
    "de": {"nodata": "Noch keine Daten", "setup": "Statuszeilen-Skript einrichten",
           "nolimits": "Keine Limitdaten", "plan": "Nur mit Claude-Abo (Pro, Max)",
           "reset": "zurückgesetzt", "asof": "Stand"},
    "en": {"nodata": "No data yet", "setup": "Set up the status-line script",
           "nolimits": "No limit data", "plan": "Only with a Claude plan (Pro, Max)",
           "reset": "reset", "asof": "As of"},
}


def validate(options: dict) -> None:
    """No options beyond those of the page."""


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _reset_text(resets_at: float, now: datetime, lang: str) -> str:
    left = resets_at - now.timestamp()
    if left < 24 * 3600:
        minutes = int(left // 60)
        return f"in {minutes // 60}:{minutes % 60:02d}"
    at = datetime.fromtimestamp(resets_at, now.tzinfo)
    return f"{WEEKDAYS[lang][at.weekday()]} {at:%H:%M}"


def fetch(options: dict, ctx) -> dict:
    lang = options["lang"]
    texts = TEXT[lang]
    pushed = ctx.pushed(CHANNEL)
    if pushed is None:
        return {"message": texts["nodata"], "sub": texts["setup"]}

    received = datetime.fromtimestamp(pushed.received_at, ctx.now.tzinfo)
    stand = f"{texts['asof']} {received:%H:%M}"
    limits = pushed.data.get("rate_limits")
    rows = []
    for key, labels in WINDOWS:
        window = limits.get(key) if isinstance(limits, dict) else None
        if not isinstance(window, dict):
            continue
        percent = _number(window.get("used_percentage"))
        if percent is None:
            continue
        resets_at = _number(window.get("resets_at"))
        if resets_at is None:
            reset = ""
        elif resets_at <= ctx.now.timestamp():
            percent, reset = 0.0, texts["reset"]
        else:
            reset = _reset_text(resets_at, ctx.now, lang)
        rows.append({"label": labels[lang], "reset": reset, "percent": percent,
                     "text": f"{round(percent)} %"})
    if not rows:
        return {"message": texts["nolimits"], "sub": texts["plan"], "stand": stand}
    return {"rows": rows, "stand": stand}
