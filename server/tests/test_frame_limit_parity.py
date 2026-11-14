"""The device rejects frames larger than kMaxFrameBytes; the server must never send one."""

import re
from pathlib import Path

from glancebox.render import MAX_JPEG_BYTES

HEADER = Path(__file__).resolve().parents[2] / "firmware" / "lib" / "core" / "poll_timing.h"


def test_firmware_frame_limit_matches_server():
    m = re.search(r"kMaxFrameBytes\s*=\s*(\d+)\s*;", HEADER.read_text(encoding="utf-8"))
    assert m, f"kMaxFrameBytes not found in {HEADER}"
    assert int(m.group(1)) == MAX_JPEG_BYTES
