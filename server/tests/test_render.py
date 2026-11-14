import io
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

from glancebox.render import MAX_JPEG_BYTES, Renderer, RenderError, encode_jpeg

pytestmark = pytest.mark.browser


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


async def test_render_html_umlauts():
    async with Renderer() as r:
        out = await r.render_html("<p>Grüße</p>")
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"
    assert img.size == (240, 240)


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
