from glancebox.frames import _jinja_env


def _render(expr: str) -> str:
    tpl = '{% import "ui.html" as ui %}' + expr
    return _jinja_env([]).from_string(tpl).render()


def test_bar_level_thresholds():
    assert "ui-ok" in _render('{{ ui.bar(74, "x") }}')
    assert "ui-warn" in _render('{{ ui.bar(75, "x") }}')
    assert "ui-bad" in _render('{{ ui.bar(90, "x") }}')


def test_bar_width_is_clamped():
    assert "width:100%" in _render('{{ ui.bar(130, "x") }}')
    assert "width:0%" in _render('{{ ui.bar(-5, "x") }}')


def test_level_returns_class_name_only():
    assert _render("{{ ui.level(10) }}") == "ui-ok"
    assert _render("{{ ui.level(80) }}") == "ui-warn"
    assert _render("{{ ui.level(95) }}") == "ui-bad"


def test_header_alert_class():
    assert "ui-alert" in _render('{{ ui.header("T", "14:05", alert=True) }}')
    out = _render('{{ ui.header("T", "14:05") }}')
    assert "ui-alert" not in out and "14:05" in out


def test_notice_escapes_and_tones():
    out = _render('{{ ui.notice("<b>", sub="<i>", tone="warn") }}')
    assert "&lt;b&gt;" in out and "&lt;i&gt;" in out and "<b>" not in out
    assert "ui-tone-warn" in out
