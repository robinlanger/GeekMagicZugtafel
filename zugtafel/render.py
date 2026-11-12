"""Rendert die Abfahrtstafel als 240×240-Bild."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .departures import Departure

SIZE = 240
HEADER_H = 34
PAD = 7
BOTTOM_MARGIN = 6   # Gehäuserahmen verdeckt sonst die letzte Zeile
BASE_ROW_H = 41     # Zeilenhöhe, für die die Grundschriftgrößen gelten

BG = (8, 10, 14)
HEADER_BG = (0, 55, 110)
FG = (235, 238, 242)
MUTED = (140, 148, 160)
DIVIDER = (38, 42, 50)
ORANGE = (255, 170, 40)
RED = (240, 70, 60)
YELLOW = (255, 215, 0)

log = logging.getLogger(__name__)

# Mitgelieferte Schriften zuerst, damit Umlaute überall gleich aussehen.
FONT_DIRS = [
    os.environ.get("FONT_DIR", ""),
    os.path.join(os.path.dirname(__file__), "fonts"),
    "/usr/share/fonts/truetype/dejavu",
]


@lru_cache(maxsize=None)
def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for d in FONT_DIRS:
        path = os.path.join(d, name)
        if d and os.path.exists(path):
            return ImageFont.truetype(path, size)
    log.warning("Schrift %s nicht gefunden – Notschrift ohne Umlaute wird verwendet", name)
    return ImageFont.load_default(size=size)


def _fit(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: float) -> str:
    if draw.textlength(text, font=fnt) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=fnt) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _badge_color(train: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    t = train.upper()
    if t.startswith("S"):
        return (0, 135, 75), (255, 255, 255)
    if t.startswith(("ICE", "IC", "EC", "FLX", "NJ")):
        return (235, 235, 235), (200, 0, 30)
    if t.startswith(("RE", "RB", "RS", "IRE")):
        return (190, 25, 40), (255, 255, 255)
    return (90, 95, 110), (255, 255, 255)


def _header(draw: ImageDraw.ImageDraw, title: str, now: datetime) -> None:
    draw.rectangle((0, 0, SIZE, HEADER_H), fill=HEADER_BG)
    f_time = font("DejaVuSans-Bold.ttf", 18)
    clock = now.strftime("%H:%M")
    clock_w = draw.textlength(clock, font=f_time)
    draw.text((SIZE - PAD - clock_w, HEADER_H / 2), clock, font=f_time, fill=FG, anchor="lm")
    f_title = font("DejaVuSansCondensed-Bold.ttf", 16)
    draw.text((PAD, HEADER_H / 2), _fit(draw, title, f_title, SIZE - 3 * PAD - clock_w),
              font=f_title, fill=FG, anchor="lm")


def _row(draw: ImageDraw.ImageDraw, dep: Departure, y: int, h: int, now: datetime) -> None:
    # Schrift wächst mit der Zeilenhöhe: weniger Zeilen = größere Schrift
    k = max(1.0, min(1.5, h / BASE_ROW_H))
    sz = lambda base: round(base * k)
    f_badge = font("DejaVuSansCondensed-Bold.ttf", sz(13))
    f_dest = font("DejaVuSansCondensed-Bold.ttf", sz(15))
    f_info = font("DejaVuSansCondensed.ttf", sz(13))
    f_info_b = font("DejaVuSansCondensed-Bold.ttf", sz(13))
    f_min = font("DejaVuSans-Bold.ttf", sz(16))

    line1 = y + h * 0.31
    line2 = y + h * 0.74

    # Linien-Badge
    bg, fg = _badge_color(dep.train)
    badge = _fit(draw, dep.train, f_badge, 68 * k)
    bw = draw.textlength(badge, font=f_badge) + 10 * k
    bh = 9 * k
    draw.rounded_rectangle((PAD, line1 - bh, PAD + bw, line1 + bh), radius=round(4 * k), fill=bg)
    draw.text((PAD + bw / 2, line1), badge, font=f_badge, fill=fg, anchor="mm")

    # Minuten bis Abfahrt (rechts oben)
    unit = ""
    if dep.cancelled:
        right, right_color = "fällt aus", RED
        f_right = f_info_b
    else:
        mins = dep.minutes_until(now)
        if mins <= 0:
            right = "jetzt"
        elif mins < 60:
            right, unit = str(mins), "min"
        else:
            right = dep.realtime(now).strftime("%H:%M")
        right_color = YELLOW if mins <= 3 else FG
        f_right = f_min
    # Zahl groß, Einheit klein dahinter – spart Platz fürs Ziel
    uw = draw.textlength(" " + unit, font=f_info) if unit else 0
    rw = draw.textlength(right, font=f_right) + uw
    draw.text((SIZE - PAD - rw, line1), right, font=f_right, fill=right_color, anchor="lm")
    if unit:
        draw.text((SIZE - PAD - uw, line1 + 1), " " + unit, font=f_info, fill=MUTED, anchor="lm")

    # Ziel
    dest_x = PAD + bw + 6
    dest_color = MUTED if dep.cancelled else FG
    max_w = SIZE - PAD - rw - 6 - dest_x
    dest = dep.destination
    if draw.textlength(dest, font=f_dest) > max_w and dest.endswith(" Hbf"):
        dest = dest[:-4]  # "Wiesbaden Hbf" -> "Wiesbaden", wenn's eng wird
    # Wenn's immer noch nicht passt: Schrift bis auf Grundgröße verkleinern, dann kürzen
    for size in range(sz(15), 14, -1):
        f_dest = font("DejaVuSansCondensed-Bold.ttf", size)
        if draw.textlength(dest, font=f_dest) <= max_w:
            break
    dest = _fit(draw, dest, f_dest, max_w)
    draw.text((dest_x, line1), dest, font=f_dest, fill=dest_color, anchor="lm")
    if dep.cancelled:
        dw = draw.textlength(dest, font=f_dest)
        draw.line((dest_x, line1, dest_x + dw, line1), fill=RED, width=2)

    # Zweite Zeile: Planzeit, Verspätung (nur wenn vorhanden), Gleis
    x = PAD
    draw.text((x, line2), dep.scheduled, font=f_info, fill=MUTED, anchor="lm")
    x += draw.textlength(dep.scheduled, font=f_info) + 6
    if not dep.cancelled and dep.delay and dep.delay > 0:
        draw.text((x, line2), f"+{dep.delay}", font=f_info_b,
                  fill=ORANGE if dep.delay < 6 else RED, anchor="lm")

    if dep.platform:
        plat = f"Gl. {dep.platform}"
        pw = draw.textlength(plat, font=f_info_b)
        draw.text((SIZE - PAD - pw, line2), plat, font=f_info_b,
                  fill=ORANGE if dep.platform_changed else MUTED, anchor="lm")


def _message(draw: ImageDraw.ImageDraw, text: str, sub: str | None = None) -> None:
    f = font("DejaVuSans-Bold.ttf", 17)
    cy = HEADER_H + (SIZE - HEADER_H - BOTTOM_MARGIN) / 2
    draw.text((SIZE / 2, cy - (10 if sub else 0)), text, font=f, fill=FG, anchor="mm")
    if sub:
        draw.text((SIZE / 2, cy + 16), sub, font=font("DejaVuSans.ttf", 13), fill=MUTED, anchor="mm")


def render(title: str, departures: list[Departure] | None, now: datetime,
           error: str | None = None, rows: int = 4) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    _header(draw, title, now)

    if error:
        _message(draw, "Keine Daten", error)
        return img
    if not departures:
        _message(draw, "Keine Abfahrten")
        return img

    rows = max(1, min(rows, 6))
    row_h = (SIZE - HEADER_H - BOTTOM_MARGIN) // rows
    for i, dep in enumerate(departures[:rows]):
        y = HEADER_H + i * row_h
        _row(draw, dep, y, row_h, now)
        if i < rows - 1:
            draw.line((PAD, y + row_h - 1, SIZE - PAD, y + row_h - 1), fill=DIVIDER)
    return img
