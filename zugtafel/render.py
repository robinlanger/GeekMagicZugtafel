"""Rendert die Abfahrtstafel als 240×240-Bild."""

from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .departures import Departure

SIZE = 240
HEADER_H = 34
PAD = 6

BG = (8, 10, 14)
HEADER_BG = (0, 55, 110)
FG = (235, 238, 242)
MUTED = (140, 148, 160)
DIVIDER = (38, 42, 50)
GREEN = (60, 200, 110)
ORANGE = (255, 170, 40)
RED = (240, 70, 60)
YELLOW = (255, 215, 0)

FONT_DIRS = [
    os.environ.get("FONT_DIR", ""),
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/Library/Fonts",
]


@lru_cache(maxsize=None)
def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for d in FONT_DIRS:
        path = os.path.join(d, name)
        if d and os.path.exists(path):
            return ImageFont.truetype(path, size)
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
    f_badge = font("DejaVuSansCondensed-Bold.ttf", 13)
    f_dest = font("DejaVuSansCondensed-Bold.ttf", 15)
    f_info = font("DejaVuSansCondensed.ttf", 13)
    f_info_b = font("DejaVuSansCondensed-Bold.ttf", 13)
    f_min = font("DejaVuSans-Bold.ttf", 16)

    line1 = y + h * 0.30
    line2 = y + h * 0.74

    # Linien-Badge
    bg, fg = _badge_color(dep.train)
    badge = _fit(draw, dep.train, f_badge, 68)
    bw = draw.textlength(badge, font=f_badge) + 10
    draw.rounded_rectangle((PAD, line1 - 9, PAD + bw, line1 + 9), radius=4, fill=bg)
    draw.text((PAD + bw / 2, line1), badge, font=f_badge, fill=fg, anchor="mm")

    # Minuten bis Abfahrt (rechts oben)
    if dep.cancelled:
        right, right_color = "fällt aus", RED
        f_right = f_info_b
    else:
        mins = dep.minutes_until(now)
        right = "jetzt" if mins <= 0 else f"{mins} min" if mins < 60 else dep.realtime(now).strftime("%H:%M")
        right_color = YELLOW if mins <= 3 else FG
        f_right = f_min
    rw = draw.textlength(right, font=f_right)
    draw.text((SIZE - PAD - rw, line1), right, font=f_right, fill=right_color, anchor="lm")

    # Ziel
    dest_x = PAD + bw + 6
    dest_color = MUTED if dep.cancelled else FG
    dest = _fit(draw, dep.destination, f_dest, SIZE - PAD - rw - 6 - dest_x)
    draw.text((dest_x, line1), dest, font=f_dest, fill=dest_color, anchor="lm")
    if dep.cancelled:
        dw = draw.textlength(dest, font=f_dest)
        draw.line((dest_x, line1, dest_x + dw, line1), fill=RED, width=2)

    # Zweite Zeile: Planzeit, Verspätung, Gleis
    x = PAD
    draw.text((x, line2), dep.scheduled, font=f_info, fill=MUTED, anchor="lm")
    x += draw.textlength(dep.scheduled, font=f_info) + 6
    if not dep.cancelled:
        if dep.delay is None:
            delay_txt, delay_col = "", MUTED
        elif dep.delay <= 0:
            delay_txt, delay_col = "pünktlich", GREEN
        else:
            delay_txt = f"+{dep.delay}"
            delay_col = ORANGE if dep.delay < 6 else RED
        if delay_txt:
            draw.text((x, line2), delay_txt, font=f_info_b, fill=delay_col, anchor="lm")

    if dep.platform:
        plat = f"Gl. {dep.platform}"
        pw = draw.textlength(plat, font=f_info_b)
        draw.text((SIZE - PAD - pw, line2), plat, font=f_info_b,
                  fill=ORANGE if dep.platform_changed else MUTED, anchor="lm")


def _message(draw: ImageDraw.ImageDraw, text: str, sub: str | None = None) -> None:
    f = font("DejaVuSans-Bold.ttf", 17)
    cy = HEADER_H + (SIZE - HEADER_H) / 2
    draw.text((SIZE / 2, cy - (10 if sub else 0)), text, font=f, fill=FG, anchor="mm")
    if sub:
        draw.text((SIZE / 2, cy + 16), sub, font=font("DejaVuSans.ttf", 13), fill=MUTED, anchor="mm")


def render(title: str, departures: list[Departure] | None, now: datetime,
           error: str | None = None, rows: int = 5) -> Image.Image:
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
    row_h = (SIZE - HEADER_H) // rows
    for i, dep in enumerate(departures[:rows]):
        y = HEADER_H + i * row_h
        _row(draw, dep, y, row_h, now)
        if i < rows - 1:
            draw.line((PAD, y + row_h - 1, SIZE - PAD, y + row_h - 1), fill=DIVIDER)
    return img
