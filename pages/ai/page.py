"""AI usage page (ai): limits or costs of one AI provider, selected with `provider:`.

Each provider module in providers/ has NAME (default header title), validate(options) and
fetch(options, ctx) -> dict with the keys of EMPTY below that it sets. `options["lang"]` is
already resolved (page option, else the top-level lang) when the provider's fetch runs.
"""

from __future__ import annotations

from types import ModuleType

from .providers import claude

LANGS = ("de", "en")

# Only the claude provider reads pushed data (from the Claude Code status-line script).
PUSH_KEYS = {"claude": ("rate_limits",)}

PROVIDERS: dict[str, ModuleType] = {
    "claude": claude,
}

# Template data shared by all providers. rows: [{"label", "reset", "percent": float, "text"}];
# big: None or {"label", "value"}; stand: "Stand 13:58" or None; message replaces the body.
EMPTY = {"rows": [], "big": None, "stand": None, "message": None, "sub": None}


def validate(options: dict) -> None:
    provider = options.get("provider")
    if provider not in PROVIDERS:
        raise ValueError(f"provider must be one of: {', '.join(PROVIDERS)}")
    if options.get("lang", "de") not in LANGS:
        raise ValueError("lang must be 'de' or 'en'")
    title = options.get("title")
    if title is not None and not isinstance(title, str):
        raise ValueError("title must be text")
    PROVIDERS[provider].validate(options)


def fetch(options: dict, ctx) -> dict:
    lang = options.get("lang", ctx.lang if ctx.lang in LANGS else "de")
    provider = PROVIDERS[options["provider"]]
    data = {**EMPTY, **provider.fetch({**options, "lang": lang}, ctx)}
    data["title"] = options.get("title") or provider.NAME
    data["clock"] = ctx.now.strftime("%H:%M")
    return data
