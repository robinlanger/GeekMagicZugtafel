"""Provider xai-api: prepaid credit balance of an xAI team (USD).

Verified 2026-11-15 against https://docs.x.ai/developers/rest-api-reference/management/billing
and https://docs.x.ai/developers/rest-api-reference/management:
- GET https://management-api.x.ai/v1/billing/teams/{team_id}/prepaid/balance
- Header: Authorization: Bearer <management key> (xAI Console -> Settings -> Management Keys;
  it is separate from the inference API key).
- Response: {"changes": [...], "total": {"val": "<USD cents as string>"}}. Purchases count
  negative and spend positive, so total "-1000" after a $10 purchase means $10.00 of credit:
  balance = -total / 100. No pagination.
"""

from __future__ import annotations

from urllib.parse import quote

from glancebox import http

from . import _cost

NAME = "xAI API"
URL = "https://management-api.x.ai/v1/billing/teams/{team}/prepaid/balance"


def validate(options: dict) -> None:
    _cost.require_text(options, "key")
    _cost.require_text(options, "team_id")
    if "budget" in options:
        raise ValueError("budget is not supported for xai-api (it shows the balance)")


def fetch(options: dict, ctx) -> dict:
    def load():
        page = http.get_json(URL.format(team=quote(options["team_id"], safe="")),
                             headers={"Authorization": f"Bearer {options['key']}"})
        return -float(page["total"]["val"]) / 100, None

    return _cost.show("xai-api", options, ctx, "balance", load)
