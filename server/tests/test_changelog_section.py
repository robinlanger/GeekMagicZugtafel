import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "changelog_section.py"
REPO = SCRIPT.parents[1]

SAMPLE = """# Changelog

## [Unreleased]

## [0.2.0] - 2026-12-01

### Added
- Two

## [0.1.0] - 2026-11-14

### Added
- One
"""


def run(*args: str):
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def write(tmp_path: Path) -> Path:
    f = tmp_path / "CHANGELOG.md"
    f.write_text(SAMPLE)
    return f


def test_middle_section_stops_at_next_heading(tmp_path):
    r = run("0.2.0", str(write(tmp_path)))
    assert r.returncode == 0
    assert r.stdout == "### Added\n- Two\n"


def test_last_section_runs_to_eof(tmp_path):
    r = run("0.1.0", str(write(tmp_path)))
    assert r.returncode == 0
    assert r.stdout == "### Added\n- One\n"


def test_unknown_version_fails(tmp_path):
    r = run("9.9.9", str(write(tmp_path)))
    assert r.returncode == 1
    assert "9.9.9" in r.stderr


def test_prefix_version_does_not_match(tmp_path):
    assert run("0.2", str(write(tmp_path))).returncode == 1


def test_repo_changelog_has_current_version():
    version = (REPO / "VERSION").read_text().strip()
    r = run(version, str(REPO / "CHANGELOG.md"))
    assert r.returncode == 0 and r.stdout.strip()
