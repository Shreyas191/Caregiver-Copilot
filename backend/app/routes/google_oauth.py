"""Google Calendar OAuth routes (CC-028)."""

import json
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.integrations.google_calendar import (
    exchange_code_for_tokens,
    get_oauth_authorization_url,
    revoke_token,
)
from app.models.caregiver import Caregiver

router = APIRouter(prefix="/auth/google", tags=["google-oauth"])


@router.get("/connect")
async def google_connect(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Initiate the Google Calendar OAuth flow."""
    state = secrets.token_urlsafe(32)
    # In production, store state in a short-lived cache/session to verify callback
    url = get_oauth_authorization_url(state=state)
    return {"authorization_url": url}


@router.get("/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth redirect from Google, store the refresh token."""
    tokens = await exchange_code_for_tokens(code)

    # The caregiver is identified by their Clerk user ID embedded in the state
    # In a real implementation, retrieve the user from the state store.
    # For simplicity, we store the token against the most recently active caregiver.
    # Production: use a short-lived state<->user_id mapping in Redis.
    raise HTTPException(
        status_code=501,
        detail="Callback handler requires session-based state verification. Implement state store for production.",
    )


@router.post("/store-token")
async def store_google_token(
    request: Request,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Store Google OAuth tokens after a successful frontend-handled OAuth flow."""
    body = await request.json()
    tokens = body.get("tokens")
    if not tokens:
        raise HTTPException(status_code=400, detail="tokens field required")

    result = await db.execute(
        select(Caregiver).where(Caregiver.clerk_user_id == clerk_user_id)
    )
    caregiver = result.scalar_one_or_none()
    if caregiver is None:
        raise HTTPException(status_code=404, detail="Caregiver not found")

    caregiver.google_oauth_token = json.dumps(tokens)
    await db.flush()
    return {"status": "connected"}


@router.post("/disconnect")
async def google_disconnect(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Revoke and remove the stored Google OAuth token."""
    result = await db.execute(
        select(Caregiver).where(Caregiver.clerk_user_id == clerk_user_id)
    )
    caregiver = result.scalar_one_or_none()
    if caregiver is None:
        raise HTTPException(status_code=404, detail="Caregiver not found")

    await revoke_token(db, caregiver.id)
    return {"status": "disconnected"}


@router.get("/status")
async def google_status(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check whether Google Calendar is connected for the current caregiver."""
    result = await db.execute(
        select(Caregiver).where(Caregiver.clerk_user_id == clerk_user_id)
    )
    caregiver = result.scalar_one_or_none()
    if caregiver is None:
        raise HTTPException(status_code=404, detail="Caregiver not found")

    return {"connected": bool(caregiver.google_oauth_token)}
