"""
Read-only GMass client for the MCP server.

Wraps lib/gmass.py so the MCP server only exposes read endpoints.
Adds three things lib/gmass.py doesn't have:
  - date-range filtering on list_campaigns
  - fuzzy subject search
  - aggregate summary stats across a date range

Send/draft/list-creation functions from lib/gmass.py are intentionally NOT
re-exported here so they cannot be called from the MCP server.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Make lib/gmass.py importable when this server runs from mcp-server/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib import gmass  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────
# Re-exports (read-only)
# ──────────────────────────────────────────────────────────────────────────

get_campaign = gmass.get_campaign
get_recipients = gmass.get_recipients
get_opens = gmass.get_opens
get_clicks = gmass.get_clicks
get_replies = gmass.get_replies
get_bounces = gmass.get_bounces
get_unsubscribes = gmass.get_unsubscribes
get_non_responders = gmass.get_non_responders


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # Accept "2026-05-01" or full ISO 8601
    try:
        if len(value) == 10:
            dt = datetime.strptime(value, "%Y-%m-%d")
        else:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Could not parse date '{value}'. Use YYYY-MM-DD or ISO 8601.") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _campaign_dt(c: dict) -> datetime | None:
    """Best-effort extract of the campaign's send/created timestamp."""
    for key in ("date", "sentDate", "createdDate", "scheduledDate"):
        v = c.get(key)
        if v:
            try:
                if isinstance(v, str):
                    return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _safe_div(num: float, denom: float) -> float:
    return round(num / denom, 4) if denom else 0.0


# ──────────────────────────────────────────────────────────────────────────
# Wrapped + new
# ──────────────────────────────────────────────────────────────────────────

def list_campaigns(
    limit: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list:
    """List campaigns with optional client-side date-range filter."""
    raw = gmass.list_campaigns(limit=None)  # pull all, filter client-side
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)

    if since_dt or until_dt:
        filtered = []
        for c in raw:
            dt = _campaign_dt(c)
            if dt is None:
                continue
            if since_dt and dt < since_dt:
                continue
            if until_dt and dt > until_dt:
                continue
            filtered.append(c)
        raw = filtered

    if limit:
        raw = raw[:limit]
    return raw


def search_campaigns_by_subject(query: str, limit: int = 25) -> list:
    """Case-insensitive substring match against campaign subject lines."""
    q = (query or "").strip().lower()
    if not q:
        return []
    all_campaigns = gmass.list_campaigns()
    matches = [c for c in all_campaigns if q in (c.get("subject") or "").lower()]
    return matches[:limit]


def campaign_summary_stats(
    since: Optional[str] = None,
    until: Optional[str] = None,
    min_sends_for_top: int = 10,
) -> dict:
    """
    Aggregate stats across a date range.

    Returns total campaigns, total sends, average open/reply/bounce/click rates,
    and top 5 campaigns by reply rate (filtered to campaigns with >= min_sends_for_top).
    """
    campaigns = list_campaigns(since=since, until=until)
    if not campaigns:
        return {
            "campaign_count": 0,
            "since": since,
            "until": until,
            "note": "No campaigns matched this date range.",
        }

    totals = {"sends": 0, "opens": 0, "clicks": 0, "replies": 0, "bounces": 0, "unsubs": 0}
    rate_rows = []

    for c in campaigns:
        sends = c.get("totalRecipients") or c.get("sentCount") or 0
        opens = c.get("uniqueOpens") or c.get("opens") or 0
        clicks = c.get("uniqueClicks") or c.get("clicks") or 0
        replies = c.get("replies") or 0
        bounces = c.get("bounces") or 0
        unsubs = c.get("unsubscribes") or 0

        totals["sends"] += sends
        totals["opens"] += opens
        totals["clicks"] += clicks
        totals["replies"] += replies
        totals["bounces"] += bounces
        totals["unsubs"] += unsubs

        if sends >= min_sends_for_top:
            rate_rows.append({
                "campaign_id": c.get("campaignId"),
                "subject": c.get("subject"),
                "sends": sends,
                "reply_rate": _safe_div(replies, sends),
                "open_rate": _safe_div(opens, sends),
            })

    top_by_reply = sorted(rate_rows, key=lambda r: r["reply_rate"], reverse=True)[:5]

    return {
        "since": since,
        "until": until,
        "campaign_count": len(campaigns),
        "totals": totals,
        "averages": {
            "open_rate": _safe_div(totals["opens"], totals["sends"]),
            "click_rate": _safe_div(totals["clicks"], totals["sends"]),
            "reply_rate": _safe_div(totals["replies"], totals["sends"]),
            "bounce_rate": _safe_div(totals["bounces"], totals["sends"]),
            "unsub_rate": _safe_div(totals["unsubs"], totals["sends"]),
        },
        "top_5_by_reply_rate": top_by_reply,
        "min_sends_for_top": min_sends_for_top,
    }
