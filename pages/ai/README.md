# ai: usage of one AI provider

User documentation: [docs/en/templates/ai.md](../../docs/en/templates/ai.md) ([Deutsch](../../docs/de/templates/ai.md)). Developer notes below.

```yaml
- type: ai
  provider: claude                # required, a key of PROVIDERS in page.py
  # key: ${OPENAI_ADMIN_KEY}      # anthropic-api, openai-api, xai-api (always ${VAR})
  # budget: 50                    # anthropic-api, openai-api: optional USD budget bar
  # team_id: ${XAI_TEAM_ID}       # xai-api
  # title: Claude Max             # default: the provider's NAME
  # lang: en                      # default: top-level lang
  refresh: 30                     # claude only reads the push inbox, so this is cheap
```

- `page.py` validates `provider` and `lang`, then delegates `validate` and `fetch` to the module in `PROVIDERS`. A new provider is a module in `providers/` with `NAME`, `validate(options)` and `fetch(options, ctx)`, plus one line in `PROVIDERS`. `options["lang"]` is already resolved when the provider's `fetch` runs.
- Providers return any of the keys `rows`, `big`, `stand`, `message`, `sub`, `alert` (see `EMPTY` in `page.py`); the page fills in the rest, `title` and `clock`. `message` replaces the body with a notice.
- `claude` reads `ctx.pushed("claude")`. The data comes from `tools/statusline/glancebox-statusline.sh` (or `.ps1`), which posts Claude Code's status-line JSON to `/api/v1/push/claude`; the server keeps only `rate_limits` (`PUSH_KEYS`). Field names and units are documented at the top of `providers/claude.py`.
- The script only sends JSON that contains `"rate_limits"`, so a new session (no limits before its first answer) does not wipe the values on the display.
- `anthropic-api`, `openai-api` and `xai-api` share `providers/_cost.py`: a per-process cache of the last successful result for `CACHE_S` = 300 s, keyed by (provider, sha256(key), team_id), the money format, the budget row and the `No data` notice (red header). Errors are logged with exception type and HTTP status only, never the exception text, so keys cannot reach the log. Endpoints, headers, fields and pagination are documented at the top of each provider module. `MIN_REFRESH` stays 0 because `claude` needs 30 s.
