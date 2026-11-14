#!/usr/bin/env python3
"""Usage: changelog_section.py <version> [CHANGELOG.md]

Print the body of the "## [<version>]" section (without the heading). Exit 1 if absent.
"""
import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str | None:
    heading = re.compile(rf"^## \[{re.escape(version)}\](\s|$)")
    out: list[str] = []
    found = False
    for line in text.splitlines():
        if found and line.startswith("## "):
            break
        if found:
            out.append(line)
        elif heading.match(line):
            found = True
    if not found:
        return None
    return "\n".join(out).strip("\n") + "\n"


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = Path(argv[2]) if len(argv) == 3 else Path(__file__).resolve().parents[1] / "CHANGELOG.md"
    body = section(path.read_text(encoding="utf-8"), argv[1])
    if body is None:
        print(f"no section [{argv[1]}] in {path}", file=sys.stderr)
        return 1
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
