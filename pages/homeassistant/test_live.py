"""Live test against the simulated Home Assistant (tools/ha-sim).

Needs HA_URL and HA_TOKEN, from the environment or from the repo-root .env (set HA_ENV_FILE to
read another file). Without both, the whole module is skipped. Nothing here ever prints
the token: assert messages carry only scenario names, never option dicts.
"""
import io
import os
import re
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
REPO_DIR = PAGES_DIR.parent
KEYS = ("HA_URL", "HA_TOKEN")
NOW = datetime(2026, 11, 16, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))

REAL = ["sensor.temperatur_wohnzimmer", "sensor.hausverbrauch", "binary_sensor.fenster_bad",
        "light.licht_kuche"]


def read_env_file(path: Path) -> dict:
    """Parse NAME=value lines; only HA_URL and HA_TOKEN are returned. Missing file -> {}."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    found = {}
    for line in text.splitlines():
        line = line.strip()  # also drops a trailing \r
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export "):].strip()
        if name not in KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        found[name] = value
    return found


def credentials() -> tuple[str, str]:
    env_file = Path(os.environ.get("HA_ENV_FILE") or REPO_DIR / ".env")
    from_file = read_env_file(env_file)
    url = os.environ.get("HA_URL") or from_file.get("HA_URL", "")
    token = os.environ.get("HA_TOKEN") or from_file.get("HA_TOKEN", "")
    return url, token


URL, TOKEN = credentials()

pytestmark = [
    pytest.mark.homeassistant_live,
    pytest.mark.skipif(not (URL and TOKEN), reason="HA_URL / HA_TOKEN not set"),
]


@pytest.fixture(scope="module")
def ha():
    return load_page_types([PAGES_DIR])["homeassistant"]


def _ctx():
    return PageContext(NOW, "de", "Europe/Berlin")


def _options(entities, **kw):
    return {"url": URL, "token": TOKEN, "entities": list(entities), **kw}


def _fetch(ha, entities, **kw):
    options = _options(entities, **kw)
    ha.validate(options)
    return ha.fetch(options, _ctx())


def test_live_values(ha):
    data = _fetch(ha, REAL)
    assert data["state"] == "ok"
    items = data["items"]
    assert len(items) == len(REAL)
    for entity_id, item in zip(REAL, items, strict=True):
        assert item["value"] not in ("fehlt", "n. v."), entity_id
    assert items[0]["unit"] == "°C"
    assert items[2]["value"] in ("offen", "zu")


def test_live_missing_entity(ha):
    data = _fetch(ha, [REAL[0], "sensor.gibt_es_nicht", REAL[1]])
    assert data["state"] == "ok"
    values = [item["value"] for item in data["items"]]
    assert values[1] == "fehlt"
    assert values[0] not in ("fehlt", "n. v.")
    assert values[2] not in ("fehlt", "n. v.")


def test_live_bad_token(ha):
    assert _fetch(ha, REAL[:1], token="falsch")["state"] == "token"


def test_live_unreachable(ha):
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(URL)
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    dead = urlunsplit((parts.scheme, f"{host}:1", "", "", ""))
    assert _fetch(ha, REAL[:1], url=dead)["state"] == "error"


def test_live_kellersensor(ha):
    data = _fetch(ha, ["sensor.kellersensor"])
    assert data["state"] == "ok"
    item = data["items"][0]
    assert item["value"] == "n. v." or (
        re.fullmatch(r"−?\d+(,\d+)?", item["value"]) and item["unit"] == "°C"
    ), "unexpected kellersensor cell"


@pytest.mark.browser
async def test_live_render(ha):
    cfg = AppConfig(interval=30, timezone="Europe/Berlin", lang="de",
                    pages=(), pages_dirs=(PAGES_DIR,))
    page = PageConfig(index=0, type="homeassistant", options=_options(REAL, layout="tiles"),
                      duration=30, refresh=30)
    async with Renderer() as r:
        out = await render_page(page, ha, cfg, r, NOW.timestamp())
    assert out[:3] == b"\xff\xd8\xff"
    assert Image.open(io.BytesIO(out)).size == (240, 240)
