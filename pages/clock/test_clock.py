import io
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from glancebox.config import AppConfig, PageConfig
from glancebox.frames import render_page
from glancebox.pages import PageContext, load_page_types
from glancebox.render import Renderer

PAGES_DIR = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 14, 9, 5, tzinfo=ZoneInfo("Europe/Berlin"))  # a Saturday


@pytest.fixture
def clock():
    return load_page_types([PAGES_DIR])["clock"]


def test_fetch_german(clock):
    data = clock.fetch({}, PageContext(NOW, "de", "Europe/Berlin"))
    assert data == {"time": "09:05", "weekday": "Samstag", "date": "14.11.2026"}


def test_fetch_english_option_overrides_ctx(clock):
    data = clock.fetch({"lang": "en"}, PageContext(NOW, "de", "Europe/Berlin"))
    assert data == {"time": "09:05", "weekday": "Saturday", "date": "2026-11-14"}


def test_validate_rejects_unknown_lang(clock):
    with pytest.raises(ValueError, match="lang"):
        clock.validate({"lang": "fr"})


@pytest.mark.browser
async def test_template_renders(clock):
    cfg = AppConfig(interval=30, timezone="Europe/Berlin", lang="de",
                    pages=(), pages_dirs=(PAGES_DIR,))
    page = PageConfig(index=0, type="clock", options={}, duration=30, refresh=60)
    async with Renderer() as r:
        out = await render_page(page, clock, cfg, r, NOW.timestamp())
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and img.size == (240, 240)
    assert img.convert("L").getextrema()[1] > 150  # bright text on the dark background
