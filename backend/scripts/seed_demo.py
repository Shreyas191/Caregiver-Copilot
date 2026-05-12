"""Seed realistic demo data for the Caregiver Co-Pilot frontend.

Run with:  python scripts/seed_demo.py
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import async_session_maker
# Import all models so SQLAlchemy registers every table (needed for FK resolution)
import app.models.document
import app.models.conversation
import app.models.provider_message
from app.models.care_recipient import CareRecipient
from app.models.medication import Medication
from app.models.vital import Vital
from app.models.episode import Episode
from app.models.enums import (
    ConsentBasis, SexAtBirth, VitalType, VitalSource,
    UrgencyLevel, EpisodeStatus,
)

CAREGIVER_ID = uuid.UUID("41ea2cd1-42a0-4d21-8be7-a5f487e1a097")  # real user

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def days_ago(n: int) -> datetime:
    return now_utc() - timedelta(days=n)


async def seed():
    async with async_session_maker() as db:

        # ── 1. Create / update care recipient ──────────────────────────────
        cr_id = uuid.UUID("6f4de724-1bdd-4539-a065-b7b604a00b8c")

        await db.execute(text("""
            UPDATE care_recipients SET
                display_name = 'Eleanor Kaldate',
                date_of_birth = '1948-03-15',
                sex_at_birth = 'female',
                conditions = '[
                    {"name": "Hypertension", "icd10": "I10", "since": "2015"},
                    {"name": "Type 2 Diabetes", "icd10": "E11", "since": "2018"},
                    {"name": "Atrial Fibrillation", "icd10": "I48", "since": "2021"},
                    {"name": "Osteoarthritis (knee)", "icd10": "M17.1", "since": "2019"}
                ]'::jsonb,
                allergies = '[
                    {"substance": "Penicillin", "reaction": "hives", "severity": "moderate"},
                    {"substance": "Sulfa drugs", "reaction": "rash", "severity": "mild"}
                ]'::jsonb,
                baseline_notes = 'Mild cognitive decline noted since 2023. Sleeps poorly. Uses walker for mobility. Lives alone — family checks in daily.',
                primary_provider_name = 'Dr. Sarah Mitchell',
                primary_provider_email = 'smitchell@heartwell.clinic',
                primary_provider_phone = '(617) 555-0192',
                emergency_contact_name = 'Shreyas Kaldate (son)',
                emergency_contact_phone = '(617) 555-0147',
                consent_basis = 'power_of_attorney'
            WHERE id = :id
        """), {"id": cr_id})

        print("✓ Updated care recipient: Eleanor Kaldate")

        # ── 2. Clear & re-seed medications ─────────────────────────────────
        await db.execute(text("DELETE FROM medications WHERE care_recipient_id = :id"), {"id": cr_id})

        meds = [
            Medication(
                care_recipient_id=cr_id,
                display_name="Lisinopril",
                rxnorm_code="29046",
                rxnorm_name="Lisinopril",
                dose="10 mg",
                frequency="once daily",
                route="oral",
                started_at=date(2015, 6, 1),
                prescribed_for="Hypertension",
                prescriber="Dr. Sarah Mitchell",
            ),
            Medication(
                care_recipient_id=cr_id,
                display_name="Metformin",
                rxnorm_code="6809",
                rxnorm_name="Metformin",
                dose="500 mg",
                frequency="twice daily with meals",
                route="oral",
                started_at=date(2018, 9, 1),
                prescribed_for="Type 2 Diabetes",
                prescriber="Dr. Sarah Mitchell",
            ),
            Medication(
                care_recipient_id=cr_id,
                display_name="Warfarin",
                rxnorm_code="11289",
                rxnorm_name="Warfarin",
                dose="5 mg",
                frequency="once daily",
                route="oral",
                started_at=date(2021, 4, 15),
                prescribed_for="Atrial Fibrillation — stroke prevention",
                prescriber="Dr. Sarah Mitchell",
            ),
            Medication(
                care_recipient_id=cr_id,
                display_name="Aspirin",
                rxnorm_code="1191",
                rxnorm_name="Aspirin",
                dose="81 mg",
                frequency="once daily",
                route="oral",
                started_at=date(2021, 4, 15),
                prescribed_for="Cardiovascular protection",
                prescriber="Dr. Sarah Mitchell",
            ),
            Medication(
                care_recipient_id=cr_id,
                display_name="Atorvastatin",
                rxnorm_code="83367",
                rxnorm_name="Atorvastatin",
                dose="40 mg",
                frequency="once at bedtime",
                route="oral",
                started_at=date(2020, 1, 10),
                prescribed_for="High cholesterol",
                prescriber="Dr. Sarah Mitchell",
            ),
            Medication(
                care_recipient_id=cr_id,
                display_name="Metoprolol",
                rxnorm_code="41493",
                rxnorm_name="Metoprolol Succinate",
                dose="25 mg",
                frequency="once daily",
                route="oral",
                started_at=date(2021, 4, 15),
                prescribed_for="Atrial Fibrillation — rate control",
                prescriber="Dr. Sarah Mitchell",
            ),
        ]
        for m in meds:
            db.add(m)

        print(f"✓ Added {len(meds)} medications")

        # ── 3. Clear & re-seed vitals (30 days of data) ────────────────────
        await db.execute(text("DELETE FROM vitals WHERE care_recipient_id = :id"), {"id": cr_id})

        vitals = []

        # Blood pressure — readings every 2-3 days, trending slightly elevated
        bp_readings = [
            (30, 158, 94), (28, 162, 96), (26, 155, 90), (24, 160, 92),
            (21, 148, 88), (19, 152, 90), (17, 165, 98), (15, 145, 85),
            (12, 150, 88), (10, 158, 92), (8, 142, 82), (6, 155, 90),
            (4, 160, 95), (2, 148, 86), (0, 153, 89),
        ]
        for days, sys_val, dia_val in bp_readings:
            vitals.append(Vital(
                care_recipient_id=cr_id,
                type=VitalType.blood_pressure,
                value_systolic=sys_val,
                value_diastolic=dia_val,
                unit="mmHg",
                recorded_at=days_ago(days).replace(hour=8, minute=0, second=0),
                source=VitalSource.manual,
            ))

        # Heart rate
        hr_readings = [(29, 78), (25, 82), (20, 76), (15, 88), (10, 80), (5, 74), (1, 77)]
        for days, bpm in hr_readings:
            vitals.append(Vital(
                care_recipient_id=cr_id,
                type=VitalType.heart_rate,
                value_numeric=bpm,
                unit="bpm",
                recorded_at=days_ago(days).replace(hour=8, minute=5, second=0),
                source=VitalSource.manual,
            ))

        # Blood glucose — fasting morning readings
        glucose_readings = [
            (30, 142), (27, 138), (24, 155), (21, 148), (18, 162),
            (15, 145), (12, 158), (9, 140), (6, 135), (3, 152), (0, 148),
        ]
        for days, mg_dl in glucose_readings:
            vitals.append(Vital(
                care_recipient_id=cr_id,
                type=VitalType.glucose,
                value_numeric=mg_dl,
                unit="mg/dL",
                recorded_at=days_ago(days).replace(hour=7, minute=30, second=0),
                source=VitalSource.manual,
                notes="Fasting",
            ))

        # Weight
        weight_readings = [(28, 68.2), (21, 68.5), (14, 68.0), (7, 67.8), (0, 68.1)]
        for days, kg in weight_readings:
            vitals.append(Vital(
                care_recipient_id=cr_id,
                type=VitalType.weight,
                value_numeric=kg,
                unit="kg",
                recorded_at=days_ago(days).replace(hour=9, minute=0, second=0),
                source=VitalSource.manual,
            ))

        # Oxygen saturation
        spo2_readings = [(20, 96), (15, 97), (10, 95), (5, 96), (1, 97)]
        for days, pct in spo2_readings:
            vitals.append(Vital(
                care_recipient_id=cr_id,
                type=VitalType.oxygen_saturation,
                value_numeric=pct,
                unit="%",
                recorded_at=days_ago(days).replace(hour=8, minute=10, second=0),
                source=VitalSource.manual,
            ))

        for v in vitals:
            db.add(v)

        print(f"✓ Added {len(vitals)} vitals")

        # ── 4. Clear & re-seed episodes ────────────────────────────────────
        await db.execute(text("DELETE FROM episodes WHERE care_recipient_id = :id"), {"id": cr_id})

        episodes = [
            Episode(
                care_recipient_id=cr_id,
                started_at=days_ago(17),
                caregiver_description=(
                    "Mom said she felt dizzy this morning and nearly fell getting out of bed. "
                    "Blood pressure was 165/98 when I checked. She seemed confused for about 10 minutes."
                ),
                symptoms=[
                    {"name": "dizziness", "severity": "moderate", "onset": "morning"},
                    {"name": "near-fall", "severity": "moderate"},
                    {"name": "transient confusion", "severity": "mild", "duration": "10 minutes"},
                ],
                agent_assessment=(
                    "Dizziness with near-fall and transient confusion in context of elevated BP (165/98). "
                    "Consider orthostatic hypotension given morning onset. "
                    "Transient confusion warrants same-day evaluation to rule out TIA."
                ),
                urgency_level=UrgencyLevel.same_day,
                recommended_actions=[
                    {"action": "Contact Dr. Mitchell today for same-day evaluation"},
                    {"action": "Check BP again in 1 hour lying, sitting, standing to assess orthostatic changes"},
                    {"action": "Ensure she does not drive until evaluated"},
                ],
                status=EpisodeStatus.resolved,
                resolved_at=days_ago(15),
                resolution_notes="Saw Dr. Mitchell — BP med dose adjusted. No TIA found on exam.",
            ),
            Episode(
                care_recipient_id=cr_id,
                started_at=days_ago(8),
                caregiver_description=(
                    "Mom's ankle and foot are swollen — noticed it when she was putting on shoes. "
                    "She says it started 2 days ago. No pain. She's been sitting more than usual this week."
                ),
                symptoms=[
                    {"name": "ankle swelling", "side": "bilateral", "severity": "mild"},
                    {"name": "reduced activity", "severity": "mild"},
                ],
                agent_assessment=(
                    "Bilateral ankle edema, likely dependent edema given reduced mobility. "
                    "On warfarin — rule out DVT. Also consider worsening cardiac or renal function given AF history."
                ),
                urgency_level=UrgencyLevel.same_day,
                recommended_actions=[
                    {"action": "Call Dr. Mitchell — same-day evaluation for DVT rule-out"},
                    {"action": "Elevate legs when seated"},
                    {"action": "Monitor for shortness of breath or chest pain — call 911 if present"},
                ],
                status=EpisodeStatus.monitoring,
            ),
            Episode(
                care_recipient_id=cr_id,
                started_at=days_ago(3),
                caregiver_description=(
                    "Mom told me she's been skipping her evening Metformin for the past week because "
                    "it upsets her stomach. Fasting glucose this morning was 162."
                ),
                symptoms=[
                    {"name": "GI discomfort", "trigger": "Metformin", "severity": "mild"},
                    {"name": "medication non-adherence"},
                ],
                agent_assessment=(
                    "Metformin GI side effects causing non-adherence, resulting in elevated glucose (162 mg/dL). "
                    "Extended-release formulation may reduce GI side effects. Warrants pharmacist or physician review."
                ),
                urgency_level=UrgencyLevel.routine,
                recommended_actions=[
                    {"action": "Ask Dr. Mitchell about switching to Metformin ER"},
                    {"action": "Take Metformin with food and water to reduce GI symptoms"},
                    {"action": "Monitor glucose daily until adherence is restored"},
                ],
                status=EpisodeStatus.open,
            ),
            Episode(
                care_recipient_id=cr_id,
                started_at=days_ago(1),
                caregiver_description=(
                    "Mom complained of a dry, persistent cough for the past 3 days. "
                    "No fever, no shortness of breath. She thinks it might be allergies."
                ),
                symptoms=[
                    {"name": "dry cough", "duration": "3 days", "severity": "mild"},
                ],
                agent_assessment=(
                    "Dry persistent cough is a well-known side effect of ACE inhibitors like Lisinopril (10-15% of patients). "
                    "Given timing and character of cough, ACE inhibitor-induced cough is the most likely cause. "
                    "If confirmed, switching to an ARB (e.g., losartan) would resolve cough while maintaining BP control."
                ),
                urgency_level=UrgencyLevel.routine,
                recommended_actions=[
                    {"action": "Mention cough to Dr. Mitchell at next visit"},
                    {"action": "Ask about switching from Lisinopril to an ARB if cough persists"},
                    {"action": "Monitor for worsening — seek care if cough becomes productive or breathing worsens"},
                ],
                status=EpisodeStatus.open,
            ),
        ]

        for ep in episodes:
            db.add(ep)

        print(f"✓ Added {len(episodes)} episodes")

        await db.commit()
        print("\n✅ Demo data seeded successfully!")
        print(f"   Care recipient: Eleanor Kaldate (ID: {cr_id})")
        print(f"   → {len(meds)} medications (incl. Warfarin + Aspirin interaction)")
        print(f"   → {len(vitals)} vital readings over 30 days")
        print(f"   → {len(episodes)} health episodes")


if __name__ == "__main__":
    asyncio.run(seed())
