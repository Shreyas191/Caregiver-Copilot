import uuid
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.integrations.rxnav import search_medications
from app.schemas.medication import (
    MedicationCreateRequest,
    MedicationResponse,
    MedicationSuggestion,
    MedicationUpdateRequest,
)
from app.services.medication_service import MedicationService


router = APIRouter(prefix="", tags=["medications"])


@router.get("/medications/search", response_model=list[MedicationSuggestion])
async def search_medications_endpoint(
    q: str = Query(..., description="The medication name to search for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search medications via NIH RxNav API.
    Provides autocomplete suggestions.
    """
    return await search_medications(db, q)


@router.post(
    "/care-recipients/{care_recipient_id}/medications",
    response_model=MedicationResponse,
    status_code=201
)
async def create_medication(
    care_recipient_id: uuid.UUID = Path(...),
    request: MedicationCreateRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a medication for a specific care recipient.
    """
    service = MedicationService(db)
    return await service.create_medication(str(care_recipient_id), request)


@router.patch("/medications/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: uuid.UUID = Path(...),
    request: MedicationUpdateRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a medication (e.g., mark as stopped).
    """
    service = MedicationService(db)
    return await service.update_medication(str(medication_id), request)


@router.get(
    "/care-recipients/{care_recipient_id}/medications",
    response_model=list[MedicationResponse]
)
async def list_medications(
    care_recipient_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all medications for a specific care recipient.
    """
    service = MedicationService(db)
    return await service.get_medications_for_recipient(str(care_recipient_id))
