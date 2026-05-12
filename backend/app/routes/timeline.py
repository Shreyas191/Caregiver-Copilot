"""Timeline API route (CC-036).

Returns a unified chronological feed of episodes, vitals, medication changes,
and document uploads for a care recipient.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.document import Document
from app.models.episode import Episode
from app.models.medication import Medication
from app.models.vital import Vital
from pydantic import BaseModel

router = APIRouter(prefix="/care-recipients", tags=["timeline"])


class TimelineEvent(BaseModel):
    id: uuid.UUID
    type: Literal["episode", "vital", "medication", "document"]
    occurred_at: datetime
    title: str
    detail: dict[str, Any]


@router.get("/{care_recipient_id}/timeline", response_model=list[TimelineEvent])
async def get_timeline(
    care_recipient_id: uuid.UUID,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    types: str | None = Query(None, description="Comma-separated types to include: episode,vital,medication,document"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[TimelineEvent]:
    """Return a unified chronological timeline for a care recipient."""
    wanted = set(types.split(",")) if types else {"episode", "vital", "medication", "document"}
    events: list[TimelineEvent] = []

    if "episode" in wanted:
        stmt = (
            select(Episode)
            .where(Episode.care_recipient_id == care_recipient_id)
            .order_by(Episode.started_at.desc())
            .limit(limit)
        )
        if start:
            stmt = stmt.where(Episode.started_at >= start)
        if end:
            stmt = stmt.where(Episode.started_at <= end)
        rows = (await db.execute(stmt)).scalars().all()
        for ep in rows:
            events.append(
                TimelineEvent(
                    id=ep.id,
                    type="episode",
                    occurred_at=ep.started_at,
                    title=f"Episode: {ep.urgency_level.value} — {ep.caregiver_description[:60]}",
                    detail={
                        "urgency_level": ep.urgency_level.value,
                        "status": ep.status.value,
                        "caregiver_description": ep.caregiver_description,
                        "agent_assessment": ep.agent_assessment,
                        "symptoms": ep.symptoms,
                        "recommended_actions": ep.recommended_actions,
                    },
                )
            )

    if "vital" in wanted:
        stmt = (
            select(Vital)
            .where(Vital.care_recipient_id == care_recipient_id)
            .order_by(Vital.recorded_at.desc())
            .limit(limit)
        )
        if start:
            stmt = stmt.where(Vital.recorded_at >= start)
        if end:
            stmt = stmt.where(Vital.recorded_at <= end)
        rows = (await db.execute(stmt)).scalars().all()
        for v in rows:
            if v.value_systolic:
                value_str = f"{v.value_systolic}/{v.value_diastolic} {v.unit}"
            elif v.value_numeric is not None:
                value_str = f"{v.value_numeric} {v.unit}"
            else:
                value_str = v.value_text or ""
            events.append(
                TimelineEvent(
                    id=v.id,
                    type="vital",
                    occurred_at=v.recorded_at,
                    title=f"{v.type.value.replace('_', ' ').title()}: {value_str}",
                    detail={
                        "vital_type": v.type.value,
                        "value_numeric": float(v.value_numeric) if v.value_numeric else None,
                        "value_systolic": v.value_systolic,
                        "value_diastolic": v.value_diastolic,
                        "value_text": v.value_text,
                        "unit": v.unit,
                        "source": v.source.value,
                        "notes": v.notes,
                    },
                )
            )

    if "medication" in wanted:
        stmt = (
            select(Medication)
            .where(Medication.care_recipient_id == care_recipient_id)
            .order_by(Medication.started_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).scalars().all()
        for med in rows:
            started = datetime(med.started_at.year, med.started_at.month, med.started_at.day)
            if start and started < start:
                continue
            if end and started > end:
                continue
            action = "Started" if not med.stopped_at else "Stopped"
            occurred = datetime(
                med.stopped_at.year, med.stopped_at.month, med.stopped_at.day
            ) if med.stopped_at and action == "Stopped" else started
            events.append(
                TimelineEvent(
                    id=med.id,
                    type="medication",
                    occurred_at=occurred,
                    title=f"{action} {med.display_name}",
                    detail={
                        "display_name": med.display_name,
                        "dose": med.dose,
                        "frequency": med.frequency,
                        "started_at": str(med.started_at),
                        "stopped_at": str(med.stopped_at) if med.stopped_at else None,
                        "prescribed_for": med.prescribed_for,
                    },
                )
            )

    if "document" in wanted:
        stmt = (
            select(Document)
            .where(Document.care_recipient_id == care_recipient_id)
            .order_by(Document.uploaded_at.desc())
            .limit(limit)
        )
        if start:
            stmt = stmt.where(Document.uploaded_at >= start)
        if end:
            stmt = stmt.where(Document.uploaded_at <= end)
        rows = (await db.execute(stmt)).scalars().all()
        for doc in rows:
            events.append(
                TimelineEvent(
                    id=doc.id,
                    type="document",
                    occurred_at=doc.uploaded_at,
                    title=f"Document: {doc.original_filename or doc.type.value}",
                    detail={
                        "document_type": doc.type.value,
                        "status": doc.status.value,
                        "original_filename": doc.original_filename,
                        "storage_path": doc.storage_path,
                    },
                )
            )

    # Sort all events chronologically (most recent first) and apply limit
    events.sort(key=lambda e: e.occurred_at, reverse=True)
    return events[:limit]
