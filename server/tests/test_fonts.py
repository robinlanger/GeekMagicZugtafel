from pathlib import Path

from PIL import ImageFont

import glancebox

FONT_DIR = Path(glancebox.__file__).parent / "fonts"


def test_bundled_fonts_have_umlauts():
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
                 "DejaVuSansCondensed.ttf", "DejaVuSansCondensed-Bold.ttf"):
        f = ImageFont.truetype(str(FONT_DIR / name), 13)
        assert f.getmask("ü").getbbox() is not None, name
