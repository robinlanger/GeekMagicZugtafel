"""Render HTML or URLs to a 240x240 baseline JPEG using one shared Chromium."""

import asyncio
import base64
import contextlib
import io
from functools import cache
from pathlib import Path
from typing import Self

from PIL import Image
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

MAX_JPEG_BYTES = 24576
QUALITY_STEPS = (85, 75, 65, 55, 45, 40)
SIZE = 240

FONTS_DIR = Path(__file__).parent / "fonts"
_FONTS = (
    ("DejaVuSans.ttf", "normal", "normal"),
    ("DejaVuSans-Bold.ttf", "bold", "normal"),
    ("DejaVuSansCondensed.ttf", "normal", "condensed"),
    ("DejaVuSansCondensed-Bold.ttf", "bold", "condensed"),
)


class RenderError(Exception):
    """Rendering failed (browser error, timeout, or image too large)."""


@cache
def font_face_css() -> str:
    """Inline @font-face rules for the bundled DejaVu fonts (built once)."""
    rules = []
    for filename, weight, variant in _FONTS:
        data = base64.b64encode((FONTS_DIR / filename).read_bytes()).decode("ascii")
        family = "DejaVu Sans Condensed" if variant == "condensed" else "DejaVu Sans"
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
            f"src:url(data:font/ttf;base64,{data}) format('truetype');}}"
        )
    return "\n".join(rules)


def encode_jpeg(png: bytes) -> bytes:
    """Encode PNG bytes as baseline JPEG, lowering quality until it fits."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    for quality in QUALITY_STEPS:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, progressive=False, optimize=True)
        if buf.tell() <= MAX_JPEG_BYTES:
            return buf.getvalue()
    raise RenderError(f"JPEG larger than {MAX_JPEG_BYTES} bytes even at quality {QUALITY_STEPS[-1]}")


class Renderer:
    """Async context manager holding one Chromium instance."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        try:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch()
        except Exception as exc:
            await self.__aexit__(None, None, None)
            raise RenderError(f"cannot start Chromium: {exc}") from exc
        return self

    async def __aexit__(self, *exc) -> None:
        browser, pw = self._browser, self._pw
        self._browser = self._pw = None
        try:
            if browser:
                await browser.close()
        finally:
            if pw:
                await pw.stop()

    def healthy(self) -> bool:
        """True while the shared Chromium is running and connected."""
        return self._browser is not None and self._browser.is_connected()

    async def _relaunch(self) -> None:
        # Chromium died (crash, OOM kill): start a fresh one instead of failing forever.
        old, self._browser = self._browser, None
        if old is not None:
            with contextlib.suppress(Exception):
                await old.close()
        try:
            self._browser = await self._pw.chromium.launch()
        except Exception as exc:
            raise RenderError(f"cannot restart Chromium: {exc}") from exc

    async def render_html(self, html: str, timeout_s: float = 10) -> bytes:
        async def load(page):
            await page.set_content(html, wait_until="load", timeout=timeout_s * 1000)

        return await self._render(load, timeout_s)

    async def render_url(
        self, url: str, wait_ms: int, wait_for: str | None, timeout_s: float
    ) -> bytes:
        async def load(page):
            await page.goto(url, wait_until="load", timeout=timeout_s * 1000)
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout_s * 1000)
            if wait_ms:
                await page.wait_for_timeout(wait_ms)

        return await self._render(load, timeout_s + wait_ms / 1000)

    async def _render(self, load, budget_s: float) -> bytes:
        if self._pw is None:
            raise RenderError("renderer not started")
        async with self._lock:
            if not self.healthy():
                await self._relaunch()
            context = page = None
            try:
                async with asyncio.timeout(budget_s + 2):
                    context = await self._browser.new_context(
                        viewport={"width": SIZE, "height": SIZE}, device_scale_factor=1
                    )
                    page = await context.new_page()
                    await load(page)
                    png = await page.screenshot(
                        type="png", clip={"x": 0, "y": 0, "width": SIZE, "height": SIZE}
                    )
            except (PlaywrightError, TimeoutError) as exc:
                raise RenderError(f"render failed: {exc}") from exc
            finally:
                for obj in (page, context):
                    if obj is not None:
                        with contextlib.suppress(PlaywrightError):
                            await obj.close()
        return encode_jpeg(png)
