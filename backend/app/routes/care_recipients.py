from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.care_recipient import CareRecipientCreateRequest, CareRecipientResponse
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
