import io
from pathlib import Path

from PIL import Image

from glancebox.config import AppConfig, PageConfig
from glancebox.frames import FrameStore, refresh_once
from glancebox.pages import PageType


class FakeRenderer:
    def __init__(self, fail_html: set[str] | None = None):
        self.html_calls: list[str] = []
        self.url_calls: list[str] = []
        self.fail_html = fail_html or set()

    async def render_html(self, html, timeout_s=10):
        self.html_calls.append(html)
        for marker in self.fail_html:
            if marker in html:
                raise RuntimeError("boom")
        return b"jpeg:" + html.encode()

    async def render_url(self, url, wait_ms, wait_for, timeout_s):
        self.url_calls.append(url)
        return b"url:" + url.encode()


def make_cfg(*pages: PageConfig) -> AppConfig:
    return AppConfig(30, "Europe/Berlin", "de", tuple(pages), ())


def script_type(tmp_path: Path, name: str, fetch, template="<p>{{ v }}</p>") -> PageType:
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    if template is not None:
        (d / "template.html").write_text(template)
    return PageType(name, "script", fetch=fetch, template_path=d / "template.html")


def page(index, type_, refresh=60, **options) -> PageConfig:
    return PageConfig(index, type_, options, 30, refresh, True)


async def test_refresh_respects_interval(tmp_path):
    t = script_type(tmp_path, "a", lambda o, c: {"v": "x"})
    cfg = make_cfg(page(0, "a", 60))
    r, store = FakeRenderer(), FrameStore()
    await refresh_once(cfg, {"a": t}, r, store, 0)
    await refresh_once(cfg, {"a": t}, r, store, 30)
    assert len(r.html_calls) == 1
    await refresh_once(cfg, {"a": t}, r, store, 61)
    assert len(r.html_calls) == 2
    assert store.get(0, 61).jpeg.startswith(b"jpeg:")


async def test_failing_page_does_not_block_others(tmp_path):
    def bad(o, c):
        raise ValueError("nope")

    types = {"bad": script_type(tmp_path, "bad", bad),
             "ok": script_type(tmp_path, "ok", lambda o, c: {"v": "fine"})}
    cfg = make_cfg(page(0, "bad"), page(1, "ok"))
    store = FrameStore()
    await refresh_once(cfg, types, FakeRenderer(), store, 0)
    assert store.available(0) == [False, True]
    assert "nope" in store.last_error(0)
    assert store.last_error(1) is None


async def test_render_failure_keeps_last_good_frame(tmp_path):
    n = {"i": 0}

    def fetch(o, c):
        n["i"] += 1
        return {"v": "bad" if n["i"] > 1 else "good"}

    t = script_type(tmp_path, "a", fetch)
    cfg = make_cfg(page(0, "a", 10))
    store, r = FrameStore(), FakeRenderer(fail_html={"bad"})
    await refresh_once(cfg, {"a": t}, r, store, 0)
    await refresh_once(cfg, {"a": t}, r, store, 11)
    assert store.get(0, 11).jpeg == b"jpeg:<p>good</p>"
    assert store.last_error(0) is not None


async def test_missing_template_fails_page_only(tmp_path):
    t = script_type(tmp_path, "a", lambda o, c: {}, template=None)
    ok = PageType("url", "url")
    cfg = make_cfg(page(0, "a"), page(1, "url", url="http://x"))
    store, r = FrameStore(), FakeRenderer()
    await refresh_once(cfg, {"a": t, "url": ok}, r, store, 0)
    assert store.available(0) == [False, True]
    assert store.last_error(0)
    assert r.url_calls == ["http://x"]


async def test_fetch_timeout(tmp_path, monkeypatch):
    from glancebox import frames
    monkeypatch.setattr(frames, "FETCH_TIMEOUT_S", 0.05)
    import time
    t = script_type(tmp_path, "a", lambda o, c: time.sleep(0.3) or {"v": 1})
    store = FrameStore()
    await refresh_once(make_cfg(page(0, "a")), {"a": t}, FakeRenderer(), store, 0)
    assert store.available(0) == [False]
    assert store.last_error(0)


async def test_context_uses_page_lang_and_tz(tmp_path):
    seen = {}

    def fetch(o, c):
        seen["ctx"] = c
        return {"v": 1}

    t = script_type(tmp_path, "a", fetch)
    cfg = make_cfg(page(0, "a", lang="en"))
    await refresh_once(cfg, {"a": t}, FakeRenderer(), FrameStore(), 0)
    assert seen["ctx"].lang == "en"
    assert seen["ctx"].now.tzinfo is not None
    assert seen["ctx"].timezone == "Europe/Berlin"


def test_stale_after_600s():
    store = FrameStore()
    store.put(0, b"x", 0)
    assert store.get(0, 599) is not None
    assert store.get(0, 601) is None


def test_etag_changes_across_store_instances():
    a, b = FrameStore(), FrameStore()
    a.put(0, b"same", 0)
    b.put(0, b"same", 0)
    assert a.get(0, 0).etag != b.get(0, 0).etag


def test_static_error_frame_is_valid_jpeg():
    store = FrameStore()
    img = Image.open(io.BytesIO(store.error_frame.jpeg))
    assert img.format == "JPEG" and img.size == (240, 240)


async def test_build_error_frame_uses_renderer():
    r = FakeRenderer()
    store = FrameStore()
    await store.build_error_frame(r)
    assert store.error_frame.jpeg.startswith(b"jpeg:")
    assert "Keine Daten" in r.html_calls[0]


async def test_build_error_frame_failure_keeps_fallback():
    r = FakeRenderer(fail_html={"Keine"})
    store = FrameStore()
    before = store.error_frame
    await store.build_error_frame(r)
    assert store.error_frame is before
