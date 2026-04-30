from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.medication import Medication
from app.models.care_recipient import CareRecipient
from app.repositories.medication import MedicationRepository
from app.schemas.medication import MedicationCreateRequest, MedicationUpdateRequest


class MedicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MedicationRepository(db)

    async def get_medications_for_recipient(
        self, care_recipient_id: str
    ) -> list[Medication]:
        # RLS will implicitly filter to allowed caregivers
        result = await self.db.execute(
            select(Medication)
            .where(Medication.care_recipient_id == care_recipient_id)
            .order_by(Medication.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_medication(
        self, medication_id: str
    ) -> Medication:
        result = await self.db.execute(
            select(Medication).where(Medication.id == medication_id)
        )
        medication = result.scalar_one_or_none()
        if not medication:
            raise HTTPException(status_code=404, detail="Medication not found")
        return medication

    async def create_medication(
        self, care_recipient_id: str, request: MedicationCreateRequest
    ) -> Medication:
        # Check if the care recipient exists (and is accessible via RLS)
        result = await self.db.execute(
            select(CareRecipient).where(CareRecipient.id == care_recipient_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Care Recipient not found")

        create_data = request.model_dump()
        medication = await self.repo.create(
            care_recipient_id=care_recipient_id,
            **create_data
        )
        return medication

    async def update_medication(
        self, medication_id: str, request: MedicationUpdateRequest
    ) -> Medication:
        medication = await self.get_medication(medication_id)
        
        update_data = request.model_dump(exclude_unset=True)
        updated_medication = await self.repo.update(medication_id, **update_data)
        
        return updated_medication

    async def delete_medication(
        self, medication_id: str
    ) -> bool:
        await self.get_medication(medication_id) # ensure exists and accessible
        return await self.repo.delete(medication_id)
