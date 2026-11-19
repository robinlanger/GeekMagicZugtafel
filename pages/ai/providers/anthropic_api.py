"""Provider anthropic-api: Claude API cost of the current month (USD), optional budget bar.

Verified 2026-11-15 against
https://platform.claude.com/docs/en/api/beta/organization/analytics/cost/list and
https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api:
- GET https://api.anthropic.com/v1/organizations/analytics/cost (Usage and Cost Analytics API,
  beta). It replaces the legacy GET /v1/organizations/cost_report, which the docs mark
  "[Legacy] ... For new integrations, use GET /v1/organizations/analytics/cost".
- Headers: x-api-key: <Admin API key sk-ant-admin...>, anthropic-version: 2026-10-21 (the
  version in the docs' examples), anthropic-beta: analytics-usage-cost-2026-08-24 (required).
- Query: starting_at (RFC 3339, >= 2026-01-01, range <= 31 days). Without group_by[] and
  time_bucket_width a single row aggregates starting_at .. min(now, starting_at + 31 days).
- Response: data[].cost.amount is a decimal string in cents ("41280.000000" = $412.80);
  data_refreshed_at (RFC 3339 or null) is the export the answer comes from, typically
  refreshed every 4 hours. Pagination: has_more, next_page -> pass as `page`.
"""

from __future__ import annotations

from datetime import datetime

from glancebox import http

from . import _cost

NAME = "Anthropic API"
URL = "https://api.anthropic.com/v1/organizations/analytics/cost"
VERSION = "2026-10-21"
BETA = "analytics-usage-cost-2026-08-24"


def validate(options: dict) -> None:
    _cost.require_text(options, "key")
    _cost.validate_budget(options)


def _parse_time(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value)


def fetch(options: dict, ctx) -> dict:
    def load():
        headers = {"x-api-key": options["key"], "anthropic-version": VERSION,
                   "anthropic-beta": BETA}
        params = {"starting_at": f"{_cost.month_start(ctx.now):%Y-%m-%dT%H:%M:%SZ}"}

        def get_page(cursor):
            return http.get_json(URL, params={**params, "page": cursor} if cursor else params,
                                 headers=headers)

        pages = _cost.paginate(get_page)
        cents = sum(float(row["cost"]["amount"]) for page in pages for row in page["data"])
        return cents / 100, _parse_time(pages[-1].get("data_refreshed_at"))

    return {**_cost.show("anthropic-api", options, ctx, "month", load), "theme": "claude"}
