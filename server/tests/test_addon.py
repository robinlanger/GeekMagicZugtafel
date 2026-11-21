import logging

from glancebox.addon import (
    STARTER_CONFIG,
    HaInfo,
    ensure_config,
    ha_defaults,
    is_addon,
    lang_from_ha,
    secrets_env,
)
from glancebox.config import load_config
from glancebox.pages import load_page_types, validate_config


def test_is_addon_needs_both(tmp_path):
    opts = tmp_path / "options.json"
    opts.write_text("{}")
    assert is_addon({"SUPERVISOR_TOKEN": "t"}, opts)
    assert not is_addon({}, opts)
    assert not is_addon({"SUPERVISOR_TOKEN": "t"}, tmp_path / "missing.json")


def test_secrets_env_fixed_and_extra(caplog):
    caplog.set_level(logging.WARNING)
    env = secrets_env({"push_key": "p" * 16, "openai_admin_key": "",
                       "extra_secrets": [{"name": "MY_API", "value": "s3cret"},
                                         {"name": "PATH", "value": "evil"},
                                         {"name": "GLANCEBOX_PUSH_KEY", "value": "x"},
                                         {"name": "bad-name", "value": "x"}]},
                      {"PATH": "/usr/bin"})
    assert env == {"GLANCEBOX_PUSH_KEY": "p" * 16, "MY_API": "s3cret"}
    assert "evil" not in caplog.text and "s3cret" not in caplog.text
    assert "PATH" in caplog.text


def test_secrets_env_skips_missing_and_none():
    assert secrets_env({"push_key": None, "extra_secrets": None}, {}) == {}
    assert secrets_env({}, {}) == {}


def test_ensure_config_writes_once(tmp_path):
    p = tmp_path / "config.yaml"
    assert ensure_config(p, tmp_path / "fb") == (p, True)
    text = p.read_text()
    assert "type: weather" in text and "latitude" not in text
    p.write_text("pages:\n  - type: clock\n")
    assert ensure_config(p, tmp_path / "fb") == (p, True)
    assert p.read_text() == "pages:\n  - type: clock\n"


def test_ensure_config_falls_back_when_not_writable(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        path, own = ensure_config(ro / "config.yaml", tmp_path / "fb")
    finally:
        ro.chmod(0o700)
    assert own is False
    assert path == tmp_path / "fb" / "config.yaml" and path.exists()


def test_lang_from_ha():
    assert lang_from_ha("de") == "de"
    assert lang_from_ha("en-GB") == "en"
    assert lang_from_ha("fr") == "en"
    assert lang_from_ha(None) == "en"


def test_ha_defaults_fill_only_missing():
    info = HaInfo("America/New_York", "en-GB", 40.7, -74.0)
    hook = ha_defaults(info, {"SUPERVISOR_TOKEN": "sup", "GLANCEBOX_PUSH_KEY": "k" * 16})
    data = {"pages": [{"type": "weather"}, {"type": "weather", "location": "Paris"},
                      {"type": "homeassistant", "entities": ["sensor.a"]},
                      {"type": "homeassistant", "url": "http://other:8123", "token": "t",
                       "entities": ["sensor.a"]}]}
    out = hook(data)
    assert out["timezone"] == "America/New_York" and out["lang"] == "en"
    assert out["push_key"] == "k" * 16
    assert out["pages"][0]["latitude"] == 40.7 and out["pages"][0]["longitude"] == -74.0
    assert "latitude" not in out["pages"][1]
    assert out["pages"][2]["url"] == "http://supervisor/core"
    assert out["pages"][2]["token"] == "sup"
    assert out["pages"][3]["url"] == "http://other:8123" and out["pages"][3]["token"] == "t"
    assert data["pages"][0] == {"type": "weather"}  # input not mutated


def test_ha_defaults_yaml_wins():
    hook = ha_defaults(HaInfo("America/New_York", "en", 1.0, 2.0), {"SUPERVISOR_TOKEN": "s"})
    out = hook({"timezone": "Europe/Berlin", "lang": "de", "pages": [{"type": "clock"}]})
    assert (out["timezone"], out["lang"]) == ("Europe/Berlin", "de")
    assert "push_key" not in out


def test_starter_config_validates(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(STARTER_CONFIG)
    hook = ha_defaults(HaInfo("Europe/Berlin", "de", 50.0, 8.0), {"SUPERVISOR_TOKEN": "s"})
    cfg = load_config(p, defaults=hook)
    validate_config(cfg, load_page_types(cfg.pages_dirs))
    assert [pg.type for pg in cfg.pages] == ["clock", "weather"]
    assert cfg.pages[1].options["latitude"] == 50.0
