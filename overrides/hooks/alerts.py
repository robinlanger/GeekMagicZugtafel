"""MkDocs hook: render GitHub alerts (> [!WARNING] ...) as Material admonitions.

The docs are read on GitHub and on the site. GitHub understands its alert syntax, Python-Markdown
does not and would print "[!WARNING]" as text. Fenced code blocks are left alone.
"""

import re

_ALERT = re.compile(r"^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_KIND = {"NOTE": "note", "TIP": "tip", "IMPORTANT": "info", "WARNING": "warning", "CAUTION": "danger"}


def github_alerts_to_admonitions(markdown: str) -> str:
    lines = markdown.split("\n")
    out: list[str] = []
    fence = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _FENCE.match(line)
        if m:
            fence = m.group(1) if fence is None else (None if m.group(1) == fence else fence)
        alert = None if fence else _ALERT.match(line)
        if not alert:
            out.append(line)
            i += 1
            continue
        out.append(f"!!! {_KIND[alert.group(1)]}")
        i += 1
        while i < len(lines) and lines[i].startswith(">"):
            body = lines[i][1:]
            body = body.removeprefix(" ")
            out.append(f"    {body}" if body.strip() else "")
            i += 1
    return "\n".join(out)


def on_page_markdown(markdown, **kwargs):
    return github_alerts_to_admonitions(markdown)
