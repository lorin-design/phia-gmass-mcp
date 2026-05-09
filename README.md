# phia-gmass-mcp

Read-only MCP server wrapping the GMass API, deployed to Render.

The full source-of-truth docs live in `phia-outreach/mcp-server/README.md`. This repo is a deploy artifact — only what Render needs to build the container.

## Tools exposed (all read-only)

- `list_campaigns` — recent campaigns with optional date range
- `get_campaign` — full stats for one campaign by ID
- `search_campaigns_by_subject` — fuzzy match by subject text
- `get_campaign_recipients` — full roster + per-recipient state
- `get_campaign_replies` — who replied
- `get_campaign_opens` — who opened
- `get_campaign_clicks` — who clicked
- `get_campaign_bounces` — who bounced
- `get_campaign_unsubscribes` — who unsubscribed
- `get_non_responders` — recipients minus repliers (for follow-up planning)
- `campaign_summary_stats` — aggregate stats across a date range

No send/draft/list-creation tools are exposed.

## Deploy

1. Push this repo to GitHub (private)
2. Render dashboard → New Web Service → connect repo
3. Render auto-detects `render.yaml` (Docker, free tier, port 8000)
4. In Environment, add `GMASS_API_KEY` with the value from the source `.env`
5. Deploy. MCP endpoint is `https://<your-render-url>/mcp`

## Connect from Claude.ai

Settings → Connectors → Add custom connector → paste `https://<your-render-url>/mcp`.

## Updating

Edit, commit, push to `main`. Render auto-deploys.
