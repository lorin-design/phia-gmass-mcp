"""
GMass API wrapper for the Phia Outreach Cockpit.

Reference: https://api.gmass.co/docs
Auth: pass API key as `apikey` query string OR `X-apikey` header.
This wrapper uses the header.

Set GMASS_API_KEY in your .env file.
"""

import os
import json
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GMASS_API_KEY")
BASE_URL = "https://api.gmass.co/api"

if not API_KEY:
    raise RuntimeError(
        "GMASS_API_KEY not set. Add it to your .env file. "
        "Get a key from GMass dashboard → Settings → API Keys → Manage API Keys."
    )

HEADERS = {"X-apikey": API_KEY, "Content-Type": "application/json"}


# ──────────────────────────────────────────────────────────────────────────
# Campaign reading (stats, reports)
# ──────────────────────────────────────────────────────────────────────────

def list_campaigns(limit: Optional[int] = None, offset: Optional[int] = None) -> list:
    """Return all campaigns with aggregate stats (sends, opens, clicks, replies, bounces, unsubs)."""
    params = {}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    r = requests.get(f"{BASE_URL}/campaigns", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def get_campaign(campaign_id: int) -> dict:
    """Get a single campaign's aggregate stats."""
    r = requests.get(f"{BASE_URL}/campaigns/{campaign_id}", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_recipients(campaign_id: int, limit: Optional[int] = None) -> list:
    """Get all recipients for a campaign."""
    params = {"limit": limit} if limit else {}
    r = requests.get(f"{BASE_URL}/reports/{campaign_id}/recipients", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def get_opens(campaign_id: int) -> list:
    r = requests.get(f"{BASE_URL}/reports/{campaign_id}/opens", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_clicks(campaign_id: int) -> list:
    r = requests.get(f"{BASE_URL}/reports/{campaign_id}/clicks", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_replies(campaign_id: int) -> list:
    """Get all recipients who replied."""
    r = requests.get(f"{BASE_URL}/reports/{campaign_id}/replies", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_bounces(campaign_id: int) -> list:
    r = requests.get(f"{BASE_URL}/reports/{campaign_id}/bounces", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_unsubscribes(campaign_id: int) -> list:
    r = requests.get(f"{BASE_URL}/reports/{campaign_id}/unsubscribes", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_non_responders(campaign_id: int) -> list:
    """Recipients who didn't reply. Useful for follow-up campaigns."""
    all_recipients = get_recipients(campaign_id)
    repliers = {r.get("emailAddress", "").lower() for r in get_replies(campaign_id)}
    return [r for r in all_recipients if r.get("emailAddress", "").lower() not in repliers]


# ──────────────────────────────────────────────────────────────────────────
# Lists & sheets (for setting up campaigns)
# ──────────────────────────────────────────────────────────────────────────

def list_sheets() -> list:
    """Get all your Google Sheets (needed for picking a list source)."""
    r = requests.get(f"{BASE_URL}/sheets", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def list_worksheets(sheet_id: str) -> list:
    """Get worksheets within a Google Sheet."""
    r = requests.get(f"{BASE_URL}/sheets/{sheet_id}/worksheets", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def create_list(spreadsheet_id: str, worksheet_id: str) -> dict:
    """Create a new GMass list alias from a Google Sheet worksheet."""
    payload = {"spreadsheetId": spreadsheet_id, "worksheetId": worksheet_id}
    r = requests.post(f"{BASE_URL}/lists", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()


# ──────────────────────────────────────────────────────────────────────────
# Drafting & sending campaigns
# ──────────────────────────────────────────────────────────────────────────

def create_draft(
    subject: str,
    message: str,
    list_address: Optional[str] = None,
    email_addresses: Optional[list] = None,
    from_email: Optional[str] = None,
    message_type: str = "html",
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict:
    """
    Create a Gmail draft for a GMass campaign.

    Pass either list_address (a GMass list alias) OR email_addresses (list of strings).
    Returns the campaign draft object including the Gmail draft ID.
    """
    if not list_address and not email_addresses:
        raise ValueError("Must provide either list_address or email_addresses.")

    payload = {
        "subject": subject,
        "message": message,
        "messageType": message_type,
    }
    if list_address:
        payload["listAddress"] = list_address
    if email_addresses:
        payload["emailAddresses"] = ",".join(email_addresses)
    if from_email:
        payload["fromEmail"] = from_email
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc

    r = requests.post(f"{BASE_URL}/campaigndrafts", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()


def send_campaign(
    campaign_draft_id: str,
    track_opens: bool = True,
    track_clicks: bool = True,
    schedule: Optional[str] = None,  # ISO datetime
    follow_ups: Optional[list] = None,
    multi_send: Optional[list] = None,
    ab_test: bool = False,
) -> dict:
    """
    Send (or schedule) a campaign from a draft.

    SAFETY: This actually sends emails. Lorin must approve before this is called.
    """
    payload = {
        "trackOpens": track_opens,
        "trackClicks": track_clicks,
    }
    if schedule:
        payload["schedule"] = schedule
    if follow_ups:
        payload["followUps"] = follow_ups
    if multi_send:
        payload["multiSend"] = ",".join(multi_send)
    if ab_test:
        payload["ABTest"] = True

    r = requests.post(
        f"{BASE_URL}/campaigns/{campaign_draft_id}",
        headers=HEADERS,
        json=payload,
    )
    r.raise_for_status()
    return r.json()


# ──────────────────────────────────────────────────────────────────────────
# Transactional (single emails, e.g. one-off intros)
# ──────────────────────────────────────────────────────────────────────────

def send_transactional(to: str, subject: str, message: str, from_email: Optional[str] = None) -> dict:
    """Send a single transactional email through Gmail."""
    payload = {
        "to": to,
        "subject": subject,
        "message": message,
    }
    if from_email:
        payload["fromEmail"] = from_email
    r = requests.post(f"{BASE_URL}/transactional", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()


# ──────────────────────────────────────────────────────────────────────────
# Account
# ──────────────────────────────────────────────────────────────────────────

def get_user() -> dict:
    """Get account info — useful for confirming the API key works."""
    r = requests.get(f"{BASE_URL}/user", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_unsubscribed_domains() -> list:
    r = requests.get(f"{BASE_URL}/unsubscribes/domains", headers=HEADERS)
    r.raise_for_status()
    return r.json()


# ──────────────────────────────────────────────────────────────────────────
# Quick CLI test
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing GMass connection…")
    user = get_user()
    print(f"✓ Connected as: {user.get('emailAddress', 'unknown')}")
    campaigns = list_campaigns(limit=5)
    print(f"✓ Pulled {len(campaigns)} recent campaigns.")
    for c in campaigns[:5]:
        print(f"  - {c.get('subject', 'no subject')} (id: {c.get('campaignId')})")
