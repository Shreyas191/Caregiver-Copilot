from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.episode import Episode
from app.models.vital import Vital
from app.schemas.care_recipient import CareRecipientCreateRequest, CareRecipientResponse
from app.schemas.episode import EpisodeResponse
from app.schemas.vital import VitalResponse
from app.services.care_recipient_service import CareRecipientService

router = APIRouter(prefix="/care-recipients", tags=["care_recipients"])


@router.post("", response_model=CareRecipientResponse, status_code=201)
async def create_care_recipient(
    request: Request,
    payload: CareRecipientCreateRequest,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new care recipient for the authenticated caregiver."""
    claims = getattr(request.state, "clerk_claims", {})
    service = CareRecipientService(db)
    return await service.create_care_recipient(clerk_user_id, claims, payload)


@router.get("", response_model=list[CareRecipientResponse])
async def list_care_recipients(
    request: Request,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all care recipients for the authenticated caregiver."""
    claims = getattr(request.state, "clerk_claims", {})
    service = CareRecipientService(db)
    return await service.get_care_recipients_for_caregiver(clerk_user_id, claims)


@router.get("/{care_recipient_id}", response_model=CareRecipientResponse)
async def get_care_recipient(
    care_recipient_id: str,
    request: Request,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific care recipient."""
    claims = getattr(request.state, "clerk_claims", {})
    service = CareRecipientService(db)
    return await service.get_care_recipient(care_recipient_id, clerk_user_id, claims)


@router.get("/{care_recipient_id}/vitals", response_model=list[VitalResponse])
async def get_care_recipient_vitals(
    care_recipient_id: str,
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get recent vitals for a specific care recipient."""
    claims = getattr(request.state, "clerk_claims", {})
    service = CareRecipientService(db)
    # Verify access before querying
    await service.get_care_recipient(care_recipient_id, clerk_user_id, claims)

    result = await db.execute(
        select(Vital)
        .where(Vital.care_recipient_id == care_recipient_id)
        .order_by(desc(Vital.recorded_at))
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{care_recipient_id}/episodes", response_model=list[EpisodeResponse])
async def get_care_recipient_episodes(
    care_recipient_id: str,
    request: Request,
    limit: int = Query(default=5, ge=1, le=100),
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get recent episodes for a specific care recipient."""
    claims = getattr(request.state, "clerk_claims", {})
    service = CareRecipientService(db)
    # Verify access before querying
    await service.get_care_recipient(care_recipient_id, clerk_user_id, claims)

    result = await db.execute(
        select(Episode)
        .where(Episode.care_recipient_id == care_recipient_id)
        .order_by(desc(Episode.started_at))
        .limit(limit)
    )
    return list(result.scalars().all())
