import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "overrides" / "hooks" / "alerts.py"
if not _PATH.exists():  # the server Docker image ships tests but not overrides/
    pytest.skip("overrides/hooks/alerts.py not in this tree", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("alerts", _PATH)
alerts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alerts)


def test_warning_becomes_admonition():
    md = "Intro\n\n> [!WARNING]\n> **No way back.** Read this.\n> Second line.\n\nAfter\n"
    out = alerts.github_alerts_to_admonitions(md)
    assert "!!! warning\n    **No way back.** Read this.\n    Second line.\n" in out
    assert "[!WARNING]" not in out
    assert out.startswith("Intro\n\n") and out.endswith("\nAfter\n")


def test_all_types_map():
    for kind, adm in [("NOTE", "note"), ("TIP", "tip"), ("IMPORTANT", "info"),
                      ("WARNING", "warning"), ("CAUTION", "danger")]:
        out = alerts.github_alerts_to_admonitions(f"> [!{kind}]\n> x\n")
        assert out.startswith(f"!!! {adm}\n    x"), kind


def test_plain_quotes_and_code_untouched():
    md = "> just a quote\n\n```\n> [!WARNING]\n> in code\n```\n"
    assert alerts.github_alerts_to_admonitions(md) == md


def test_empty_quote_line_kept_inside():
    out = alerts.github_alerts_to_admonitions("> [!NOTE]\n> a\n>\n> b\n")
    assert out == "!!! note\n    a\n\n    b\n"
