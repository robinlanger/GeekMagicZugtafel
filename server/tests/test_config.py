from pathlib import Path

import pytest

from glancebox.config import ConfigError, load_config


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return p


def test_defaults(tmp_path):
    cfg = load_config(write(tmp_path, "interval: 30\npages:\n  - type: bahn\n    station: X\n"))
    page = cfg.pages[0]
    assert (page.index, page.type) == (0, "bahn")
    assert page.duration == 30
    assert page.refresh == 30
    assert page.options == {"station": "X"}
    assert cfg.interval == 30
    assert cfg.timezone == "Europe/Berlin"
    assert cfg.lang == "de"
    assert len(cfg.pages_dirs) == 1 and cfg.pages_dirs[0].name == "pages"


def test_explicit_duration_and_refresh(tmp_path):
    cfg = load_config(write(tmp_path, "pages:\n  - {type: url, url: u, duration: 15}\n"
                                      "  - {type: url, url: u, duration: 15, refresh: 60}\n"))
    assert cfg.interval == 30
    assert (cfg.pages[0].duration, cfg.pages[0].refresh) == (15, 15)
    assert cfg.pages[1].refresh == 60


def test_empty_pages_rejected(tmp_path):
    with pytest.raises(ConfigError, match="at least one page"):
        load_config(write(tmp_path, "pages: []\n"))


def test_yaml_syntax_error_is_config_error(tmp_path):
    with pytest.raises(ConfigError, match="config.yaml"):
        load_config(write(tmp_path, "pages: [unclosed\n  - : :\n"))


def test_missing_file_is_config_error(tmp_path):
    with pytest.raises(ConfigError, match="nope.yaml"):
        load_config(tmp_path / "nope.yaml")


def test_duration_must_be_positive(tmp_path):
    with pytest.raises(ConfigError, match=r"pages\[0\]"):
        load_config(write(tmp_path, "pages:\n  - {type: bahn, duration: 0}\n"))


def test_missing_type_rejected(tmp_path):
    with pytest.raises(ConfigError, match=r"pages\[1\].*type"):
        load_config(write(tmp_path, "pages:\n  - {type: url}\n  - {url: u}\n"))


def test_unknown_top_level_key_rejected(tmp_path):
    with pytest.raises(ConfigError, match="intervall"):
        load_config(write(tmp_path, "intervall: 5\npages:\n  - {type: url}\n"))


def test_invalid_interval_rejected(tmp_path):
    with pytest.raises(ConfigError, match="interval"):
        load_config(write(tmp_path, "interval: true\npages:\n  - {type: url}\n"))


def test_custom_pages_dir_relative_to_config(tmp_path):
    cfg = load_config(write(tmp_path, "custom_pages_dir: mine\npages:\n  - {type: url}\n"))
    assert cfg.pages_dirs[-1] == (tmp_path / "mine").resolve()
    assert len(cfg.pages_dirs) == 2


def test_pages_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("GLANCEBOX_PAGES_DIR", str(tmp_path / "builtin"))
    cfg = load_config(write(tmp_path, "pages:\n  - {type: url}\n"))
    assert cfg.pages_dirs[0] == tmp_path / "builtin"
