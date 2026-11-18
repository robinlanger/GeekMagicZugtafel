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


def test_nested_file_missing_fails(tmp_path):
    make(tmp_path, {}, {})
    (tmp_path / "docs" / "en" / "templates").mkdir()
    (tmp_path / "docs" / "en" / "templates" / "x.md").write_text("# X\n")
    r = run(tmp_path)
    assert r.returncode == 1
    assert "docs/de/templates/x.md is missing" in r.stdout + r.stderr


def test_nested_matching_pair_passes(tmp_path):
    make(tmp_path, {}, {})
    for sub in ("en", "de"):
        d = tmp_path / "docs" / sub / "templates"
        d.mkdir()
        (d / "x.md").write_text("# X\n## Y\n")
    assert run(tmp_path).returncode == 0


def test_nested_heading_mismatch_fails(tmp_path):
    make(tmp_path, {}, {})
    for sub, text in (("en", "# X\n## Y\n"), ("de", "# X\n### Y\n")):
        d = tmp_path / "docs" / sub / "templates"
        d.mkdir()
        (d / "x.md").write_text(text)
    assert run(tmp_path).returncode == 1


FM_EN = "---\ntemplate: home.html\nhero_title: Your display\nlead: x\n---\n# A\n"


def test_front_matter_keys_must_match(tmp_path):
    de = "---\ntemplate: home.html\nhero_title: Dein Display\n---\n# A\n"
    make(tmp_path, {"index.md": FM_EN}, {"index.md": de})
    r = run(tmp_path)
    assert r.returncode == 1
    assert "front matter keys differ" in r.stdout + r.stderr


def test_front_matter_same_keys_pass(tmp_path):
    de = "---\ntemplate: home.html\nhero_title: Dein Display\nlead: y\n---\n# A\n"
    make(tmp_path, {"index.md": FM_EN}, {"index.md": de})
    assert run(tmp_path).returncode == 0


def test_front_matter_keys_ignores_body(tmp_path):
    de = "---\ntemplate: home.html\nhero_title: Dein Display\nlead: y\n---\n# A\nextra: not a key\n"
    make(tmp_path, {"index.md": FM_EN}, {"index.md": de})
    assert run(tmp_path).returncode == 0


FM_LIST = "---\nsteps:\n  - title: A\n    href: a/\n  - title: B\n    href: b/\n---\n# A\n"


def test_front_matter_extra_list_entry_fails(tmp_path):
    de = "---\nsteps:\n  - title: A\n    href: a/\n---\n# A\n"
    make(tmp_path, {"index.md": FM_LIST}, {"index.md": de})
    r = run(tmp_path)
    assert r.returncode == 1
    assert "front matter keys differ" in r.stdout + r.stderr


def test_front_matter_renamed_nested_key_fails(tmp_path):
    de = FM_LIST.replace("    href: b/", "    link: b/")
    make(tmp_path, {"index.md": FM_LIST}, {"index.md": de})
    assert run(tmp_path).returncode == 1


def test_front_matter_nested_values_may_differ(tmp_path):
    de = FM_LIST.replace("title: A", "title: Ä").replace("title: B", "title: Ö")
    make(tmp_path, {"index.md": FM_LIST}, {"index.md": de})
    assert run(tmp_path).returncode == 0
