from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_recipient import CareRecipient
from app.models.caregiver import Caregiver
from app.repositories.care_recipient import CareRecipientRepository
from app.schemas.care_recipient import CareRecipientCreateRequest


class CareRecipientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CareRecipientRepository(db)

    async def get_or_create_caregiver(self, clerk_user_id: str, claims: dict) -> Caregiver:
        """Ensures a caregiver row exists for the given Clerk user ID."""
        result = await self.db.execute(
            select(Caregiver).where(Caregiver.clerk_user_id == clerk_user_id)
        )
        caregiver = result.scalar_one_or_none()

        if not caregiver:
            # Clerk JWT claims sometimes contain 'email' and 'name' if requested,
            # otherwise we fall back to placeholders until they update their profile.
            email = claims.get("email", f"{clerk_user_id}@placeholder.com")
            name = claims.get("name", "Caregiver")

            caregiver = Caregiver(
                clerk_user_id=clerk_user_id,
                display_name=name,
                email=email,
                timezone="America/New_York",
            )
            self.db.add(caregiver)
            await self.db.commit()
            await self.db.refresh(caregiver)

        return caregiver

    async def create_care_recipient(
        self, clerk_user_id: str, claims: dict, request: CareRecipientCreateRequest
    ) -> CareRecipient:
        caregiver = await self.get_or_create_caregiver(clerk_user_id, claims)

        # Convert the Pydantic models to a dictionary
        create_data = request.model_dump()
        
        # We must explicitly convert the list of Pydantic models into lists of dicts
        # because the SQLAlchemy JSONB field expects raw dicts.
        # Actually, model_dump() already converts nested models to dicts by default.

        care_recipient = await self.repo.create(
            caregiver_id=caregiver.id,
            **create_data
        )
        return care_recipient

    async def get_care_recipients_for_caregiver(
        self, clerk_user_id: str, claims: dict
    ) -> list[CareRecipient]:
        caregiver = await self.get_or_create_caregiver(clerk_user_id, claims)
        # RLS implicitly filters this, but filtering explicitly is good practice
        result = await self.db.execute(
            select(CareRecipient).where(CareRecipient.caregiver_id == caregiver.id)
        )
        return list(result.scalars().all())

    async def get_care_recipient(
        self, care_recipient_id: str, clerk_user_id: str, claims: dict
    ) -> CareRecipient:
        caregiver = await self.get_or_create_caregiver(clerk_user_id, claims)
        result = await self.db.execute(
            select(CareRecipient).where(
                CareRecipient.id == care_recipient_id,
                CareRecipient.caregiver_id == caregiver.id,
            )
        )
        cr = result.scalar_one_or_none()
        if not cr:
            raise HTTPException(status_code=404, detail="Care Recipient not found")
        return cr
