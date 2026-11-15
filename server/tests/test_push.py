import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from glancebox.app import create_app
from glancebox.config import AppConfig, ConfigError, PageConfig
from glancebox.frames import FrameStore, render_page
from glancebox.pages import PageContext, PageType, load_page_types, merge_push_keys
from glancebox.push import CHANNEL_RE, MAX_BODY, Pushed, PushInbox

NOW = 1_000_000.0
KEY = "k" * 20
AUTH = {"Authorization": f"Bearer {KEY}"}
URL = "/api/v1/push/claude"
GOOD = {"rate_limits": {"five_hour": {"used_percentage": 12}}, "cwd": "/home/me"}


def push_type() -> PageType:
    return PageType("ai", "script", fetch=lambda o, c: {},
                    push_keys={"claude": ("rate_limits",)})


def make_client(push_key: str | None = KEY, types=None):
    cfg = AppConfig(30, "Europe/Berlin", "de", (), (), push_key)
    if types is None:
        types = {"ai": push_type()}
    app = create_app(cfg, FrameStore(0), lambda: NOW, types=types, start_worker=False)
    return TestClient(app), app.state.inbox


def seeded_client(**kw):
    client, inbox = make_client(**kw)
    inbox.put("claude", {"rate_limits": "old"}, 1.0)
    return client, inbox


def assert_unchanged(inbox):
    assert inbox.get("claude") == Pushed({"rate_limits": "old"}, 1.0)


def test_push_stores_allowed_keys_only():
    client, inbox = make_client()
    r = client.post(URL, json=GOOD, headers=AUTH)
    assert r.status_code == 204
    got = inbox.get("claude")
    assert got.data == {"rate_limits": {"five_hour": {"used_percentage": 12}}}
    assert got.received_at == NOW


def test_push_without_push_key_is_404():
    client, inbox = make_client(push_key=None)
    assert client.post(URL, json=GOOD, headers=AUTH).status_code == 404
    assert inbox.get("claude") is None


def test_push_without_types_is_404():
    cfg = AppConfig(30, "Europe/Berlin", "de", (), (), KEY)
    app = create_app(cfg, FrameStore(0), lambda: NOW, start_worker=False)
    assert TestClient(app).post(URL, json=GOOD, headers=AUTH).status_code == 404


@pytest.mark.parametrize("channel", ["foo", "Claude!", "claude%0A"])
def test_push_unknown_or_bad_channel_is_404(channel):
    client, inbox = seeded_client()
    r = client.post(f"/api/v1/push/{channel}", json=GOOD, headers=AUTH)
    assert r.status_code == 404
    assert_unchanged(inbox)


def test_bad_channel_is_404_even_if_declared():
    t = PageType("x", "script", fetch=lambda o, c: {}, push_keys={"claude": ("a",)})
    t.push_keys["Claude!"] = ("a",)  # bypasses load-time validation on purpose
    client, _ = make_client(types={"x": t})
    assert client.post("/api/v1/push/Claude!", json={"a": 1}, headers=AUTH).status_code == 404


@pytest.mark.parametrize("headers", [
    {"Authorization": "Bearer " + "x" * 20},
    {},
    {"Authorization": KEY},
    {"Authorization": "Bearer"},
    {"Authorization": "Basic " + KEY},
    {"Authorization": "Bearer " + KEY + "x"},
    {"Authorization": "Bearer ä".encode()},  # non-ASCII must not crash
])
def test_push_bad_auth_is_401(headers):
    client, inbox = seeded_client()
    r = client.post(URL, json=GOOD, headers=headers)
    assert r.status_code == 401
    assert_unchanged(inbox)


def test_push_body_too_large_is_413():
    client, inbox = seeded_client()
    body = json.dumps({"rate_limits": "x" * 70_000}).encode()
    r = client.post(URL, content=body, headers={**AUTH, "Content-Type": "application/json"})
    assert r.status_code == 413
    assert_unchanged(inbox)


def test_push_body_longer_than_content_length_header_claims_is_413():
    client, inbox = seeded_client()

    def chunks():
        yield b'{"rate_limits": "'
        yield b"x" * (MAX_BODY + 10)
        yield b'"}'

    # A streamed body has no Content-Length, so the length check must use the bytes read.
    r = client.post(URL, content=chunks(), headers=AUTH)
    assert r.status_code == 413
    assert_unchanged(inbox)


def test_push_exactly_max_body_is_accepted():
    client, _ = make_client()
    prefix, suffix = b'{"rate_limits": "', b'"}'
    body = prefix + b"x" * (MAX_BODY - len(prefix) - len(suffix)) + suffix
    assert len(body) == MAX_BODY
    assert client.post(URL, content=body, headers=AUTH).status_code == 204


@pytest.mark.parametrize("body", [b"[1,2]", b"{not json", b"", b"\xff\xfe", b'"str"'])
def test_push_non_object_is_422(body):
    client, inbox = seeded_client()
    r = client.post(URL, content=body, headers={**AUTH, "Content-Type": "application/json"})
    assert r.status_code == 422
    assert_unchanged(inbox)


def test_push_order_404_before_401():
    client, _ = make_client(push_key=None)
    assert client.post(URL, json=GOOD).status_code == 404
    client, _ = make_client()
    assert client.post("/api/v1/push/foo", json=GOOD).status_code == 404


def test_push_order_401_before_413_and_422():
    client, _ = make_client()
    assert client.post(URL, content=b"x" * 70_000).status_code == 401
    assert client.post(URL, content=b"[1]").status_code == 401


def test_push_replaces_previous_value():
    client, inbox = seeded_client()
    assert client.post(URL, json={"other": 1}, headers=AUTH).status_code == 204
    assert inbox.get("claude") == Pushed({}, NOW)


def test_inbox_get_unknown_is_none():
    assert PushInbox().get("nope") is None


def test_channel_re():
    assert CHANNEL_RE.fullmatch("claude") and CHANNEL_RE.fullmatch("a_b-9")
    assert not CHANNEL_RE.fullmatch("Claude") and not CHANNEL_RE.fullmatch("x" * 33)
    assert not CHANNEL_RE.fullmatch("") and not CHANNEL_RE.fullmatch("a\n")
    assert MAX_BODY == 65536


def write_page(tmp_path: Path, push_keys_src: str | None) -> Path:
    d = tmp_path / "p"
    d.mkdir()
    src = "def fetch(options, ctx):\n    return {}\n"
    if push_keys_src is not None:
        src += f"PUSH_KEYS = {push_keys_src}\n"
    (d / "page.py").write_text(src)
    return tmp_path


def test_load_push_keys(tmp_path):
    types = load_page_types([write_page(tmp_path, '{"claude": ("rate_limits", "x")}')])
    assert types["p"].push_keys == {"claude": ("rate_limits", "x")}


def test_push_keys_default_empty(tmp_path):
    types = load_page_types([write_page(tmp_path, None)])
    assert types["p"].push_keys == {}
    assert types["url"].push_keys == {}


@pytest.mark.parametrize("src", [
    '["claude"]', '{"Claude": ("a",)}', '{"claude": "a"}', '{"claude": (1,)}',
    '{"claude": ["a"]}', '{1: ("a",)}', '{"x" * 33: ("a",)}', '{"claude": ("",)}',
    '{"claude\\n": ("a",)}',
])
def test_bad_push_keys_rejected(tmp_path, src):
    with pytest.raises(ConfigError, match="PUSH_KEYS"):
        load_page_types([write_page(tmp_path, src)])


def test_merge_push_keys():
    a = PageType("a", "script", push_keys={"claude": ("x",), "other": ("o",)})
    b = PageType("b", "script", push_keys={"claude": ("y",)})
    merged = merge_push_keys({"a": a, "b": b, "url": PageType("url", "url")})
    assert merged == {"claude": frozenset({"x", "y"}), "other": frozenset({"o"})}


def test_page_context_default_pushed():
    from datetime import datetime
    ctx = PageContext(datetime(2026, 1, 1), "de", "Europe/Berlin")
    assert ctx.pushed("claude") is None


class CapturingRenderer:
    def __init__(self):
        self.html: list[str] = []

    async def render_html(self, html, timeout_s=10):
        self.html.append(html)
        return b"jpeg"


async def test_page_ctx_pushed(tmp_path):
    (tmp_path / "template.html").write_text("<p>{{ v }}|{{ at }}</p>")

    def fetch(options, ctx):
        got = ctx.pushed("claude")
        return {"v": got.data["rate_limits"], "at": got.received_at}

    t = PageType("ai", "script", fetch=fetch, template_path=tmp_path / "template.html",
                 push_keys={"claude": ("rate_limits",)})
    cfg = AppConfig(30, "Europe/Berlin", "de", (), ())
    inbox = PushInbox()
    inbox.put("claude", {"rate_limits": 42}, 7.0)
    r = CapturingRenderer()
    await render_page(PageConfig(0, "ai", {}, 30, 30), t, cfg, r, NOW, inbox)
    assert r.html == ["<p>42|7.0</p>"]


async def test_render_page_without_inbox_gives_none(tmp_path):
    (tmp_path / "template.html").write_text("<p>{{ v }}</p>")
    t = PageType("ai", "script", fetch=lambda o, c: {"v": c.pushed("claude")},
                 template_path=tmp_path / "template.html")
    r = CapturingRenderer()
    await render_page(PageConfig(0, "ai", {}, 30, 30), t,
                      AppConfig(30, "Europe/Berlin", "de", (), ()), r, NOW)
    assert r.html == ["<p>None</p>"]


async def test_refresh_once_forwards_inbox(tmp_path):
    from glancebox.frames import refresh_once

    (tmp_path / "template.html").write_text("<p>{{ v }}</p>")
    t = PageType("ai", "script", fetch=lambda o, c: {"v": c.pushed("claude").data["a"]},
                 template_path=tmp_path / "template.html")
    inbox = PushInbox()
    inbox.put("claude", {"a": "pushed"}, 1.0)
    cfg = AppConfig(30, "Europe/Berlin", "de", (PageConfig(0, "ai", {}, 30, 30),), ())
    r, store = CapturingRenderer(), FrameStore(1)
    await refresh_once(cfg, {"ai": t}, r, store, NOW, inbox)
    assert r.html == ["<p>pushed</p>"]
