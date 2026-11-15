"""Provider openai-api: OpenAI API cost of the current month (USD), optional budget bar.

Verified 2026-11-15 against
https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs
- GET https://api.openai.com/v1/organization/costs
- Header: Authorization: Bearer <Admin API key> (created at
  https://platform.openai.com/settings/organization/admin-keys).
- Query: start_time (Unix seconds, inclusive, required), bucket_width "1d" (the only value),
  limit (buckets per page, 1..180, default 7).
- Response: data[] buckets, each with results[].amount.value (a number in USD) and
  amount.currency "usd". Pagination: has_more, next_page -> pass as `page`.
"""

from __future__ import annotations

from glancebox import http

from . import _cost

NAME = "OpenAI API"
URL = "https://api.openai.com/v1/organization/costs"


def validate(options: dict) -> None:
    _cost.require_text(options, "key")
    _cost.validate_budget(options)


def fetch(options: dict, ctx) -> dict:
    def load():
        headers = {"Authorization": f"Bearer {options['key']}"}
        params = {"start_time": int(_cost.month_start(ctx.now).timestamp()),
                  "bucket_width": "1d", "limit": 31}

        def get_page(cursor):
            return http.get_json(URL, params={**params, "page": cursor} if cursor else params,
                                 headers=headers)

        pages = _cost.paginate(get_page)
        return sum(float(result["amount"]["value"]) for page in pages
                   for bucket in page["data"] for result in bucket["results"]), None

    return _cost.show("openai-api", options, ctx, "month", load)
