import subprocess
import sys

from fastapi.testclient import TestClient

from glancebox.app import create_app
from glancebox.config import AppConfig, PageConfig
from glancebox.frames import FrameStore

NOW = 1_000_000.0


def make_cfg() -> AppConfig:
    pages = (PageConfig(0, "url", {}, 30, 30), PageConfig(1, "url", {}, 30, 30))
    return AppConfig(30, "Europe/Berlin", "de", pages, ())


def make_client(store=None, now=NOW):
    cfg = make_cfg()
    store = store or FrameStore(2)
    return TestClient(create_app(cfg, store, lambda: now, start_worker=False)), store


def filled_store() -> FrameStore:
    store = FrameStore(2)
    store.put(0, b"jpeg0", NOW - 1)
    store.put(1, b"jpeg1", NOW - 1)
    store.mark_attempt(0, NOW - 1, None)
    store.mark_attempt(1, NOW - 1, None)
    return store


def test_frame_200_with_headers():
    client, _ = make_client(filled_store())
    r = client.get("/api/v1/frame?id=abc&fw=0.1.0")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.headers["etag"]
    assert 2 <= int(r.headers["x-next-in"]) <= 30
    assert r.headers["cache-control"] == "no-store"


def test_frame_304_on_matching_etag():
    client, _ = make_client(filled_store())
    first = client.get("/api/v1/frame")
    r = client.get("/api/v1/frame", headers={"If-None-Match": first.headers["etag"]})
    assert r.status_code == 304
    assert r.headers["etag"] == first.headers["etag"]
    assert 2 <= int(r.headers["x-next-in"]) <= 30


def test_stale_etag_after_restart_gets_200():
    client, _ = make_client(filled_store())
    other, _ = make_client(filled_store())
    etag = other.get("/api/v1/frame").headers["etag"]
    assert client.get("/api/v1/frame", headers={"If-None-Match": etag}).status_code == 200


def test_frame_all_pages_down_returns_error_frame():
    client, _ = make_client(FrameStore(2))
    r = client.get("/api/v1/frame")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.headers["x-next-in"] == "10"


def test_preview_and_healthz_and_index():
    client, store = make_client(filled_store())
    store.mark_attempt(1, NOW - 1, "RuntimeError: boom")
    assert client.get("/preview/0.jpg").content == b"jpeg0"
    assert client.get("/preview/5.jpg").status_code == 404
    h = client.get("/healthz").json()
    assert h["pages_ok"] == 2 and h["version"]
    html = client.get("/").text
    assert "/preview/0.jpg" in html and "boom" in html


def test_cli_bad_config_exits_2(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("pages:\n  - type: nonexistent\n")
    r = subprocess.run([sys.executable, "-m", "glancebox", "render", "0", "-o",
                        str(tmp_path / "o.png"), "--config", str(cfg)],
                       check=False, capture_output=True, text=True)
    assert r.returncode == 2
    assert "pages[0]" in r.stderr
