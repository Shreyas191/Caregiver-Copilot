"""Google Calendar OAuth integration (CC-028).

Handles the OAuth 2.0 flow and creates calendar events using stored refresh tokens.
Tokens are stored encrypted in caregivers.google_oauth_token.
"""

import json
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.caregiver import Caregiver

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
_SCOPES = "https://www.googleapis.com/auth/calendar.events"


def get_oauth_authorization_url(state: str) -> str:
    """Build the Google OAuth authorization URL."""
    settings = get_settings()
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{_GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange an OAuth authorization code for access + refresh tokens."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> str:
    """Exchange a refresh token for a fresh access token."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def _get_caregiver_by_care_recipient(
    db: AsyncSession, care_recipient_id: uuid.UUID
) -> Caregiver | None:
    """Load the caregiver who owns this care recipient."""
    from app.models.care_recipient import CareRecipient

    result = await db.execute(
        select(CareRecipient).where(CareRecipient.id == care_recipient_id)
    )
    recipient = result.scalar_one_or_none()
    if recipient is None:
        return None

    result2 = await db.execute(
        select(Caregiver).where(Caregiver.id == recipient.caregiver_id)
    )
    return result2.scalar_one_or_none()


async def create_calendar_event(
    db: AsyncSession,
    care_recipient_id: uuid.UUID,
    summary: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
) -> dict:
    """Create a Google Calendar event for the caregiver who owns this care recipient.

    Raises RuntimeError with 'not connected' in the message if the caregiver
    has not connected Google Calendar.
    """
    caregiver = await _get_caregiver_by_care_recipient(db, care_recipient_id)
    if caregiver is None or not caregiver.google_oauth_token:
        raise RuntimeError("Google Calendar not connected — no OAuth token found")

    token_data = json.loads(caregiver.google_oauth_token)
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Google Calendar not connected — refresh token missing")

    access_token = await refresh_access_token(refresh_token)

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
        "reminders": {"useDefault": True},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=event_body,
        )
        response.raise_for_status()
        return response.json()


async def revoke_token(db: AsyncSession, caregiver_id: uuid.UUID) -> None:
    """Revoke and delete the stored Google OAuth token."""
    result = await db.execute(select(Caregiver).where(Caregiver.id == caregiver_id))
    caregiver = result.scalar_one_or_none()
    if caregiver is None or not caregiver.google_oauth_token:
        return

    token_data = json.loads(caregiver.google_oauth_token)
    token = token_data.get("access_token") or token_data.get("refresh_token")

    if token:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token},
                )
        except Exception:
            pass  # Best-effort revocation

    caregiver.google_oauth_token = None
    await db.flush()
