"""
Phia GMass MCP Server (read-only).

Exposes campaign stats from GMass over MCP so colleagues can query
performance from their own Claude.ai. No send/draft/list-creation tools
are exposed — those stay in Lorin's local Claude Code.

Run locally:
    GMASS_API_KEY=... python server.py

Run in Docker / Fly.io:
    listens on $PORT (default 8000), streamable HTTP transport at /mcp
"""

from __future__ import annotations

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

import gmass_client as gm

mcp = FastMCP("phia-gmass")


# ──────────────────────────────────────────────────────────────────────────
# Campaign discovery
# ──────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_campaigns(
    limit: Optional[int] = 25,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list:
    """
    List recent GMass campaigns with their aggregate stats (sends, opens,
    replies, bounces, etc).

    Use this when someone asks "what campaigns did we send recently" or
    "show me campaigns from May". Optional `since` and `until` accept
    YYYY-MM-DD or ISO 8601 dates and filter by send date. `limit` defaults
    to 25 — increase if you need more history.
    """
    return gm.list_campaigns(limit=limit, since=since, until=until)


@mcp.tool()
def get_campaign(campaign_id: int) -> dict:
    """
    Get full aggregate stats for one campaign by its GMass campaign ID.

    Use after list_campaigns or search_campaigns_by_subject to drill into
    a specific campaign's numbers.
    """
    return gm.get_campaign(campaign_id)


@mcp.tool()
def search_campaigns_by_subject(query: str, limit: int = 25) -> list:
    """
    Find campaigns whose subject line contains the given text
    (case-insensitive substring match).

    Use this when someone references a campaign by topic or brand name
    rather than ID — e.g. "find the Margaux campaigns" or "the Memorial
    Day send".
    """
    return gm.search_campaigns_by_subject(query, limit=limit)


# ──────────────────────────────────────────────────────────────────────────
# Per-campaign breakdowns
# ──────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_campaign_recipients(campaign_id: int, limit: Optional[int] = None) -> list:
    """
    List every recipient of a campaign with their per-recipient state
    (sent, opened, clicked, replied, bounced, unsubscribed).

    Use when you need the full recipient roster for a campaign.
    """
    return gm.get_recipients(campaign_id, limit=limit)


@mcp.tool()
def get_campaign_replies(campaign_id: int) -> list:
    """
    List recipients who replied to a campaign.

    Use to see who engaged — answers "who replied to the Margaux R2 send?"
    """
    return gm.get_replies(campaign_id)


@mcp.tool()
def get_campaign_opens(campaign_id: int) -> list:
    """List recipients who opened a campaign at least once."""
    return gm.get_opens(campaign_id)


@mcp.tool()
def get_campaign_clicks(campaign_id: int) -> list:
    """List recipients who clicked a tracked link in a campaign."""
    return gm.get_clicks(campaign_id)


@mcp.tool()
def get_campaign_bounces(campaign_id: int) -> list:
    """
    List recipients whose emails bounced.

    Useful for cleaning the contact list before the next send.
    """
    return gm.get_bounces(campaign_id)


@mcp.tool()
def get_campaign_unsubscribes(campaign_id: int) -> list:
    """List recipients who unsubscribed from a campaign."""
    return gm.get_unsubscribes(campaign_id)


@mcp.tool()
def get_non_responders(campaign_id: int) -> list:
    """
    List recipients who did NOT reply to a campaign (recipients minus
    repliers).

    Use for planning follow-up sends — "who hasn't responded to the
    R1 outreach yet?"
    """
    return gm.get_non_responders(campaign_id)


# ──────────────────────────────────────────────────────────────────────────
# Aggregate analytics
# ──────────────────────────────────────────────────────────────────────────

@mcp.tool()
def campaign_summary_stats(
    since: Optional[str] = None,
    until: Optional[str] = None,
    min_sends_for_top: int = 10,
) -> dict:
    """
    Aggregate performance across a date range: total campaigns, total
    sends, average open/click/reply/bounce/unsub rates, and top 5
    campaigns by reply rate.

    Use for "how did outreach perform last month" type questions.
    `min_sends_for_top` filters tiny campaigns out of the top-5 leaderboard
    so a 2-recipient send with 1 reply doesn't dominate.
    """
    return gm.campaign_summary_stats(
        since=since, until=until, min_sends_for_top=min_sends_for_top
    )


# ──────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # FastMCP's streamable HTTP transport binds to host/port from settings.
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="streamable-http")
