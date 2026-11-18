#!/usr/bin/env python3
"""Usage: check_docs_parity.py [repo-root]. Exit 1 if the EN and DE docs drift apart.

Checks README.md <-> README.de.md and docs/en/** <-> docs/de/** (recursively, by relative path): both sides must exist and have
the same heading level sequence (headings inside fenced code blocks are ignored) and the same
top-level front-matter keys.
"""
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s")
FENCE = re.compile(r"^\s*(```|~~~)")
FM_KEY = re.compile(r"^([A-Za-z_][\w-]*):")


def levels(path: Path) -> list[int]:
    out: list[int] = []
    fence = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif fence == m.group(1):
                fence = None
            continue
        if fence is None and (h := HEADING.match(line)):
            out.append(len(h.group(1)))
    return out


def front_matter_keys(path: Path) -> list[str]:
    """Top-level keys of a leading YAML front matter block (between --- lines), in order."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    keys: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        if m := FM_KEY.match(line):
            keys.append(m.group(1))
    return []  # unterminated: not front matter


def pairs(root: Path) -> tuple[list[tuple[Path, Path]], list[str]]:
    found: list[tuple[Path, Path]] = []
    errors: list[str] = []
    en, de = root / "README.md", root / "README.de.md"
    if en.exists() and not de.exists():
        errors.append("README.de.md is missing")
    elif en.exists():
        found.append((en, de))
    en_dir, de_dir = root / "docs" / "en", root / "docs" / "de"
    def files(d: Path) -> set[str]:
        return {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and not p.name.startswith(".")} if d.is_dir() else set()

    en_files, de_files = files(en_dir), files(de_dir)
    for name in sorted(en_files - de_files):
        errors.append(f"docs/de/{name} is missing")
    for name in sorted(de_files - en_files):
        errors.append(f"docs/en/{name} is missing")
    for name in sorted(en_files & de_files):
        found.append((en_dir / name, de_dir / name))
    return found, errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    found, errors = pairs(root)
    for a, b in found:
        la, lb = levels(a), levels(b)
        if la != lb:
            errors.append(f"heading levels differ: {a.relative_to(root)} {la} vs {b.relative_to(root)} {lb}")
        if a.suffix == ".md" and front_matter_keys(a) != front_matter_keys(b):
            errors.append(f"front matter keys differ: {a.relative_to(root)} vs {b.relative_to(root)}")
    for e in errors:
        print(f"FAIL: {e}", file=sys.stderr)
    if not errors:
        print(f"OK: {len(found)} document pairs match")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
