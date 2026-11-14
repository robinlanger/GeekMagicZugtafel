import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "check_docs_parity.py"


def make(root: Path, en: dict[str, str], de: dict[str, str], readme=True, readme_de=True) -> None:
    for sub, files in (("en", en), ("de", de)):
        d = root / "docs" / sub
        d.mkdir(parents=True)
        for name, text in files.items():
            (d / name).write_text(text)
    if readme:
        (root / "README.md").write_text("# T\n")
    if readme_de:
        (root / "README.de.md").write_text("# T\n")


def run(root: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)], check=False, capture_output=True, text=True
    )


def test_matching_passes(tmp_path):
    make(tmp_path, {"a.md": "# A\n## B\n"}, {"a.md": "# Ä\n## C\n"})
    assert run(tmp_path).returncode == 0


def test_missing_file_fails(tmp_path):
    make(tmp_path, {"a.md": "# A\n", "b.md": "# B\n"}, {"a.md": "# A\n"})
    r = run(tmp_path)
    assert r.returncode == 1
    assert "b.md" in r.stdout + r.stderr


def test_missing_readme_de_fails(tmp_path):
    make(tmp_path, {"a.md": "# A\n"}, {"a.md": "# A\n"}, readme_de=False)
    assert run(tmp_path).returncode == 1


def test_heading_mismatch_fails(tmp_path):
    make(tmp_path, {"a.md": "# A\n## B\n"}, {"a.md": "# A\n### B\n"})
    assert run(tmp_path).returncode == 1


def test_headings_in_code_fences_ignored(tmp_path):
    en = "# A\n```bash\n# comment\n```\n## B\n"
    de = "# A\n~~~\n# one\n# two\n~~~\n## B\n"
    make(tmp_path, {"a.md": en}, {"a.md": de})
    assert run(tmp_path).returncode == 0


def test_file_only_in_de_fails(tmp_path):
    make(tmp_path, {"a.md": "# A\n"}, {"a.md": "# A\n", "extra.md": "# E\n"})
    r = run(tmp_path)
    assert r.returncode == 1
    assert "extra.md" in r.stderr
