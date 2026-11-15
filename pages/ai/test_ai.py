import io
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from glancebox.config import AppConfig, PageConfig
from glancebox.frames import render_page
from glancebox.pages import PageContext, load_page_types
from glancebox.push import Pushed, PushInbox

PAGES_DIR = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 11, 15, 14, 5, tzinfo=TZ)  # a Sunday
RECEIVED = datetime(2026, 11, 15, 13, 58, tzinfo=TZ).timestamp()
THURSDAY_9 = datetime(2026, 11, 19, 9, 0, tzinfo=TZ).timestamp()
IN_2H13 = (NOW + timedelta(hours=2, minutes=13, seconds=20)).timestamp()
OPTIONS = {"provider": "claude"}


def ctx(pushed: dict | None, lang: str = "de") -> PageContext:
    """Context whose inbox holds `pushed` (the stored data, i.e. only `rate_limits`)."""
    item = None if pushed is None else Pushed(pushed, RECEIVED)
    return PageContext(now=NOW, lang=lang, timezone="Europe/Berlin",
                       pushed=lambda c: item if c == "claude" else None)


def limits(five=(42.0, IN_2H13), seven=(81.0, THURSDAY_9)) -> dict:
    """Shape per https://code.claude.com/docs/en/statusline (rate_limits.*)."""
    rl = {}
    if five:
        rl["five_hour"] = {"used_percentage": five[0], "resets_at": int(five[1])}
    if seven:
        rl["seven_day"] = {"used_percentage": seven[0], "resets_at": int(seven[1])}
    return {"rate_limits": rl}


@pytest.fixture
def ai():
    return load_page_types([PAGES_DIR])["ai"]


def test_push_keys_declared(ai):
    assert ai.push_keys == {"claude": ("rate_limits",)}


def test_validate_unknown_provider(ai):
    with pytest.raises(ValueError, match="provider"):
        ai.validate({"provider": "nope"})
    with pytest.raises(ValueError, match="provider"):
        ai.validate({})
    with pytest.raises(ValueError, match="lang"):
        ai.validate({"provider": "claude", "lang": "fr"})
    ai.validate({"provider": "claude", "lang": "en", "title": "Claude Max"})


def test_claude_no_data_yet(ai):
    data = ai.fetch(OPTIONS, ctx(None))
    assert data["title"] == "Claude" and data["clock"] == "14:05"
    assert data["message"] == "Noch keine Daten"
    assert data["sub"] == "Statuszeilen-Skript einrichten"
    assert data["rows"] == [] and data["big"] is None
    en = ai.fetch(OPTIONS, ctx(None, "en"))
    assert (en["message"], en["sub"]) == ("No data yet", "Set up the status-line script")


def test_claude_rows(ai):
    data = ai.fetch(OPTIONS, ctx(limits()))
    assert data["message"] is None and data["big"] is None
    assert data["rows"] == [
        {"label": "5 Stunden", "reset": "in 2:13", "percent": 42.0, "text": "42 %"},
        {"label": "Woche", "reset": "Do 09:00", "percent": 81.0, "text": "81 %"},
    ]
    assert data["stand"] == "Stand 13:58"


def test_claude_rows_english_and_title(ai):
    data = ai.fetch({**OPTIONS, "lang": "en", "title": "Claude Max"},
                    ctx(limits(five=(7.6, IN_2H13))))
    assert data["title"] == "Claude Max"
    assert [(r["label"], r["reset"], r["text"]) for r in data["rows"]] == [
        ("5 hours", "in 2:13", "8 %"), ("Week", "Thu 09:00", "81 %")]
    assert data["stand"] == "As of 13:58"


def test_claude_reset_passed_is_zero(ai):
    past = (NOW - timedelta(minutes=1)).timestamp()
    data = ai.fetch(OPTIONS, ctx(limits(five=(97.0, past))))
    assert data["rows"][0] == {"label": "5 Stunden", "reset": "zurückgesetzt",
                               "percent": 0.0, "text": "0 %"}
    en = ai.fetch({**OPTIONS, "lang": "en"}, ctx(limits(five=(97.0, NOW.timestamp()))))
    assert en["rows"][0]["reset"] == "reset" and en["rows"][0]["percent"] == 0.0


def test_claude_missing_seven_day_shows_one_row(ai):
    data = ai.fetch(OPTIONS, ctx(limits(seven=None)))
    assert [r["label"] for r in data["rows"]] == ["5 Stunden"]
    assert data["message"] is None


def test_claude_no_windows_in_push(ai):
    for stored in ({}, {"rate_limits": {}}, {"rate_limits": "x"},
                   {"rate_limits": {"five_hour": {"used_percentage": "a", "resets_at": 1}}}):
        data = ai.fetch(OPTIONS, ctx(stored))
        assert data["rows"] == []
        assert data["message"] == "Keine Limitdaten"
        assert data["stand"] == "Stand 13:58"


@pytest.mark.browser
async def test_template_renders_claude(ai):
    cfg = AppConfig(interval=30, timezone="Europe/Berlin", lang="de",
                    pages=(), pages_dirs=(PAGES_DIR,))
    page = PageConfig(index=0, type="ai", options=OPTIONS, duration=30, refresh=30)
    from glancebox.render import Renderer

    async with Renderer() as r:
        inbox = PushInbox()
        empty = Image.open(io.BytesIO(
            await render_page(page, ai, cfg, r, NOW.timestamp(), inbox))).convert("RGB")
        inbox.put("claude", limits(five=(42.0, IN_2H13), seven=(95.0, THURSDAY_9)), RECEIVED)
        full = Image.open(io.BytesIO(
            await render_page(page, ai, cfg, r, NOW.timestamp(), inbox))).convert("RGB")
    assert empty.size == full.size == (240, 240)
    assert empty.convert("L").getextrema()[1] > 150  # the notice is visible

    def has(img, rgb):
        return any(all(abs(a - b) < 40 for a, b in zip(img.getpixel((x, y)), rgb, strict=True))
                   for x in range(0, 240, 3) for y in range(34, 232, 3))

    assert has(full, (60, 200, 110)) and has(full, (240, 70, 60))  # green 42 %, red 95 %
    assert not has(empty, (60, 200, 110))
