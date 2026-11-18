import gzip
import importlib.util
import re
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "tools" / "webasset.py"
if not _PATH.exists():  # the server Docker image ships tests but not tools/
    pytest.skip("tools/webasset.py not in this tree", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("webasset", _PATH)
webasset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(webasset)


def test_minify_css_keeps_strings_and_urls():
    out = webasset.minify_css('a { content: "a  b"; }\nb{background:url( x  y.png )}')
    assert '"a  b"' in out
    assert "url( x  y.png )" in out


def test_minify_css_removes_comments_and_space():
    out = webasset.minify_css("/* head */\nbody  {\n  color : red ;\n}\n\n.a > .b , .c { margin: 0 }\n")
    assert out == "body{color:red;}.a>.b,.c{margin:0}"


def test_minify_css_keeps_space_in_selectors_and_values():
    out = webasset.minify_css(".a .b { margin: 0 auto; font: 15px -apple-system, sans-serif }")
    assert out == ".a .b{margin:0 auto;font:15px -apple-system,sans-serif}"


def test_minify_js_keeps_strings_with_slashes():
    src = "const u = \"http://x\";\nconst v = '// no';\nconst w = `/* t */`;\n"
    out = webasset.minify_js(src)
    assert '"http://x"' in out
    assert "'// no'" in out
    assert "`/* t */`" in out


def test_minify_js_drops_comment_lines():
    src = "// top\nlet a = 1; // tail\n\n/* block\n spanning */\n    let b = 2;\n"
    out = webasset.minify_js(src)
    assert out == "let a = 1;\nlet b = 2;"


def test_gzip_reproducible_and_roundtrip():
    data = b"hello " * 100
    a = webasset.gzip_bytes(data)
    assert a == webasset.gzip_bytes(data)
    assert gzip.decompress(a) == data


def test_render_header_lengths_and_hash():
    assets = {"app_css": b"\x01\x02\x03", "app_js": b"\xff"}
    h = webasset.render_header(assets)
    assert "constexpr size_t kWeb_app_cssLen = 3;" in h
    assert "constexpr size_t kWeb_app_jsLen = 1;" in h
    assert "0x01,0x02,0x03" in h.replace(" ", "")
    m = re.search(r'kWebHash\[\] = "([0-9a-f]+)"', h)
    assert m and len(m.group(1)) == 8
    assert h == webasset.render_header(assets)
