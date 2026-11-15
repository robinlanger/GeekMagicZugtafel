#!/usr/bin/env python3
"""Render the preview images of the template catalog to docs/img/templates/<name>.png.

Each entry of SAMPLES maps a preview name to (page type, options, data). `data` is the dict the
page's fetch() would return; it goes straight into the page's template.html, so no network is
needed. Later template pages add their entries here.

Run it locally (uses the server's virtualenv, which has Chromium):

    server/.venv/bin/python tools/render_previews.py

or inside the image (tools/ is not copied into it, so mount it):

    docker run --rm -v "$PWD/docs/img:/app/docs/img" -v "$PWD/tools:/app/tools:ro" \
        glancebox:dev python /app/tools/render_previews.py
"""
import asyncio
import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from glancebox.frames import _jinja_env
from glancebox.render import Renderer

OUT = ROOT / "docs" / "img" / "templates"
PAGES = ROOT / "pages"

SAMPLES: dict[str, tuple[str, dict, dict]] = {
    "clock": ("clock", {"lang": "en"},
              {"time": "14:32", "weekday": "Thursday", "date": "2026-11-12"}),
    "weather": ("weather", {"location": "Frankfurt am Main", "lang": "en"}, {
        "title": "Frankfurt am Main", "clock": "14:32", "icon": "partly", "temp": 11,
        "desc": "Partly cloudy", "high": 15, "low": 6,
        "hours": [{"hour": "15", "temp": 12, "rain": 10}, {"hour": "16", "temp": 12, "rain": 20},
                  {"hour": "17", "temp": 10, "rain": 55}, {"hour": "18", "temp": 9, "rain": 70}]}),
    "bahn": ("bahn", {"station": "Musterstadt"}, {
        "title": "Musterstadt", "clock": "10:42", "message": None, "sub": None,
        "rows": [
            {"train": "RB 1", "badge": "regional", "destination": "Ostdorf", "right": "5",
             "unit": "min", "right_class": "", "scheduled": "10:47", "delay": 4,
             "delay_class": "minor", "platform": "Gl. 1", "platform_changed": False,
             "cancelled": False},
            {"train": "S 3", "badge": "s", "destination": "Westhafen", "right": "9",
             "unit": "min", "right_class": "", "scheduled": "10:51", "delay": None,
             "delay_class": "major", "platform": "Gl. 2", "platform_changed": True,
             "cancelled": False},
            {"train": "ICE 599", "badge": "long", "destination": "Nord Hbf", "right": "fällt aus",
             "unit": "", "right_class": "cancelled", "scheduled": "10:55", "delay": None,
             "delay_class": "major", "platform": "Gl. 3", "platform_changed": False,
             "cancelled": True},
            {"train": "RE 20", "badge": "regional", "destination": "Südstadt", "right": "2",
             "unit": "min", "right_class": "soon", "scheduled": "10:44", "delay": 8,
             "delay_class": "major", "platform": "Gl. 4", "platform_changed": False,
             "cancelled": False},
        ]}),
}


async def render_all(names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with Renderer() as renderer:
        for name in names:
            ptype, _options, data = SAMPLES[name]
            page_dir = PAGES / ptype
            html = _jinja_env([page_dir]).get_template("template.html").render(**data)
            jpeg = await renderer.render_html(html)
            buf = io.BytesIO()
            Image.open(io.BytesIO(jpeg)).convert("RGB").quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(buf, "PNG", optimize=True)
            (OUT / f"{name}.png").write_bytes(buf.getvalue())
            print(f"{name}.png  {buf.tell()} bytes")


def main(argv: list[str]) -> int:
    names = argv[1:] or list(SAMPLES)
    unknown = [n for n in names if n not in SAMPLES]
    if unknown:
        print(f"unknown sample(s): {', '.join(unknown)}; known: {', '.join(SAMPLES)}",
              file=sys.stderr)
        return 1
    asyncio.run(render_all(names))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
