import io
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

from glancebox.render import MAX_JPEG_BYTES, Renderer, RenderError, encode_jpeg


def test_encode_jpeg_baseline_and_size():
    rnd = random.Random(1)
    img = Image.frombytes("RGB", (240, 240), bytes(rnd.randrange(256) for _ in range(240 * 240 * 3)))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    out = encode_jpeg(buf.getvalue())
    assert len(out) <= MAX_JPEG_BYTES
    res = Image.open(io.BytesIO(out))
    assert not res.info.get("progressive")
    assert res.size == (240, 240)


@pytest.mark.browser
async def test_render_html_umlauts():
    async with Renderer() as r:
        out = await r.render_html("<p>Grüße</p>")
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"
    assert img.size == (240, 240)


@pytest.mark.browser
async def test_render_url_timeout_raises():
    class Slow(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(5)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        async with Renderer() as r:
            t0 = time.monotonic()
            with pytest.raises(RenderError):
                await r.render_url(f"http://127.0.0.1:{srv.server_port}/", 0, None, 1)
            assert time.monotonic() - t0 < 3
    finally:
        srv.shutdown()


@pytest.mark.browser
async def test_render_url_wait_ms_exceeds_timeout_succeeds():
    class Fast(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"<p>ok</p>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Fast)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        async with Renderer() as r:
            out = await r.render_url(f"http://127.0.0.1:{srv.server_port}/", 4000, None, 1)
        assert Image.open(io.BytesIO(out)).size == (240, 240)
    finally:
        srv.shutdown()


@pytest.mark.browser
async def test_render_relaunches_dead_browser():
    async with Renderer() as r:
        await r._browser.close()  # simulates a crashed Chromium
        assert not r.healthy()
        out = await r.render_html("<p>again</p>")
        assert r.healthy()
    assert Image.open(io.BytesIO(out)).format == "JPEG"


class _DeadBrowser:
    def is_connected(self):
        return False

    async def close(self):
        pass


class _FailingChromium:
    async def launch(self):
        raise RuntimeError("no chromium")


class _FakePlaywright:
    chromium = _FailingChromium()


async def test_render_relaunch_failure_is_render_error():
    r = Renderer()
    r._pw, r._browser = _FakePlaywright(), _DeadBrowser()
    with pytest.raises(RenderError, match="cannot restart Chromium"):
        await r.render_html("<p>x</p>")
    assert not r.healthy()
