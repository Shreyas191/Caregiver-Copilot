"""CC-050: Seed three synthetic Synthea-based demo personas.

Personas:
  1. Margaret Okafor, 76F — T2DM + Hypertension + Mild cognitive impairment
  2. Robert Chen, 68M    — Post-stroke recovery
  3. Maria Santos, 54F   — Stage 3B breast cancer (active treatment)

Each persona gets a synthetic caregiver, a care recipient record,
medications with valid RxCUIs, 30 days of vitals, and 2-3 health episodes.

Usage:
    python seed/personas.py               # seed all three
    python seed/personas.py --persona 2   # seed only Robert Chen
    python seed/personas.py --drop        # drop and re-seed all
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import async_session_maker
import app.models.document
import app.models.conversation
import app.models.provider_message
from app.models.caregiver import Caregiver
from app.models.care_recipient import CareRecipient
from app.models.medication import Medication
from app.models.vital import Vital
from app.models.episode import Episode
from app.models.enums import (
    ConsentBasis, SexAtBirth, VitalType, VitalSource,
    UrgencyLevel, EpisodeStatus,
)

# ── Deterministic UUIDs ────────────────────────────────────────────────────────

def _uid(key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, key)


PERSONAS = {
    1: {
        "caregiver_id": _uid("caregiver-james-okafor"),
        "cr_id": _uid("cr-margaret-okafor"),
        "caregiver_clerk_id": "synth_clerk_james_okafor",
        "caregiver_name": "James Okafor",
        "caregiver_email": "james.okafor@example.com",
    },
    2: {
        "caregiver_id": _uid("caregiver-linda-chen"),
        "cr_id": _uid("cr-robert-chen"),
        "caregiver_clerk_id": "synth_clerk_linda_chen",
        "caregiver_name": "Linda Chen",
        "caregiver_email": "linda.chen@example.com",
    },
    3: {
        "caregiver_id": _uid("caregiver-carlos-santos"),
        "cr_id": _uid("cr-maria-santos"),
        "caregiver_clerk_id": "synth_clerk_carlos_santos",
        "caregiver_name": "Carlos Santos",
        "caregiver_email": "carlos.santos@example.com",
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)

def _ago(days: int, hour: int = 8, minute: int = 0) -> datetime:
    return (_now() - timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)


# ── Persona builders ────────────────────────────────────────────────────────────

def _build_persona_1(ids: dict) -> dict:
    """Margaret Okafor, 76F — T2DM + Hypertension + Mild cognitive impairment."""
    cr_id = ids["cr_id"]

    medications = [
        Medication(care_recipient_id=cr_id, display_name="Lisinopril",
                   rxnorm_code="29046", rxnorm_name="Lisinopril",
                   dose="10 mg", frequency="once daily", route="oral",
                   started_at=date(2010, 3, 15), prescribed_for="Hypertension",
                   prescriber="Dr. Amara Nwosu"),
        Medication(care_recipient_id=cr_id, display_name="Metformin",
                   rxnorm_code="6809", rxnorm_name="Metformin",
                   dose="500 mg", frequency="twice daily with meals", route="oral",
                   started_at=date(2014, 8, 1), prescribed_for="Type 2 Diabetes",
                   prescriber="Dr. Amara Nwosu"),
        Medication(care_recipient_id=cr_id, display_name="Donepezil",
                   rxnorm_code="135447", rxnorm_name="Donepezil",
                   dose="5 mg", frequency="once daily at bedtime", route="oral",
                   started_at=date(2021, 2, 20), prescribed_for="Mild cognitive impairment",
                   prescriber="Dr. Patricia Osei"),
        Medication(care_recipient_id=cr_id, display_name="Atorvastatin",
                   rxnorm_code="83367", rxnorm_name="Atorvastatin",
                   dose="20 mg", frequency="once at bedtime", route="oral",
                   started_at=date(2018, 11, 10), prescribed_for="Hyperlipidemia",
                   prescriber="Dr. Amara Nwosu"),
        Medication(care_recipient_id=cr_id, display_name="Aspirin",
                   rxnorm_code="1191", rxnorm_name="Aspirin",
                   dose="81 mg", frequency="once daily", route="oral",
                   started_at=date(2019, 1, 5), prescribed_for="Cardiovascular prevention",
                   prescriber="Dr. Amara Nwosu"),
    ]

    vitals = []
    for days, sys_v, dia_v in [
        (30,155,92),(27,160,95),(24,148,88),(21,163,97),(18,150,90),
        (15,158,93),(12,145,86),(9,161,96),(6,153,91),(3,156,92),(0,149,88),
    ]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.blood_pressure,
                            value_systolic=sys_v, value_diastolic=dia_v, unit="mmHg",
                            recorded_at=_ago(days), source=VitalSource.manual))

    for days, val in [(28,138),(24,145),(20,152),(16,140),(12,148),(8,135),(4,141),(0,144)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.glucose,
                            value_numeric=val, unit="mg/dL",
                            recorded_at=_ago(days, 7, 30), source=VitalSource.manual,
                            notes="Fasting"))

    for days, bpm in [(25,74),(18,78),(11,76),(4,80)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.heart_rate,
                            value_numeric=bpm, unit="bpm",
                            recorded_at=_ago(days, 8, 5), source=VitalSource.manual))

    for days, kg in [(28,64.2),(21,64.5),(14,64.0),(7,63.8),(0,64.1)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.weight,
                            value_numeric=kg, unit="kg",
                            recorded_at=_ago(days, 9), source=VitalSource.manual))

    episodes = [
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(22),
            caregiver_description=(
                "Mom got confused while making tea this morning — left the stove on and "
                "forgot she had already taken her morning pills. This lasted about 20 minutes."
            ),
            symptoms=[
                {"name": "confusion", "duration": "20 minutes", "severity": "mild"},
                {"name": "memory lapse", "severity": "mild"},
            ],
            agent_assessment=(
                "Transient confusion with memory lapse in a patient with known mild cognitive "
                "impairment on Donepezil. Could represent a normal fluctuation or an early "
                "decompensation. Double-dosing risk identified. Recommend medication reconciliation."
            ),
            urgency_level=UrgencyLevel.same_day,
            recommended_actions=[
                {"action": "Use a pill organizer or app to prevent double-dosing"},
                {"action": "Contact Dr. Osei to report the episode and reassess Donepezil dose"},
                {"action": "Do not leave stove unattended — consider automatic stove shut-off"},
            ],
            status=EpisodeStatus.resolved,
            resolved_at=_ago(20),
            resolution_notes="Called Dr. Osei — no dose change needed. Ordered pill organizer.",
        ),
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(9),
            caregiver_description=(
                "Mom has been unusually tired for the past 4 days, sleeping 12+ hours. "
                "She says her legs feel heavy. Blood glucose was 152 this morning."
            ),
            symptoms=[
                {"name": "fatigue", "duration": "4 days", "severity": "moderate"},
                {"name": "heavy legs", "severity": "mild"},
                {"name": "hyperglycemia", "value": "152 mg/dL"},
            ],
            agent_assessment=(
                "Fatigue with elevated glucose (152) may indicate suboptimal diabetes control. "
                "Heavy legs could suggest early fluid retention or medication effect. "
                "On Lisinopril and Metformin — renal function check warranted."
            ),
            urgency_level=UrgencyLevel.routine,
            recommended_actions=[
                {"action": "Schedule labs — BMP, HbA1c, CBC"},
                {"action": "Ensure Metformin is being taken with meals (reduces fatigue)"},
                {"action": "Encourage gentle walking 10 min twice daily to reduce leg heaviness"},
            ],
            status=EpisodeStatus.monitoring,
        ),
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(2),
            caregiver_description=(
                "Mom is having trouble sleeping — wakes up 3-4 times per night. "
                "She's irritable during the day and says she can't remember where she put things."
            ),
            symptoms=[
                {"name": "insomnia", "severity": "moderate"},
                {"name": "irritability", "severity": "mild"},
                {"name": "forgetfulness", "severity": "mild"},
            ],
            agent_assessment=(
                "Sleep disruption is common with cognitive decline and may worsen cognitive symptoms. "
                "Donepezil taken at bedtime can sometimes cause vivid dreams / insomnia. "
                "Trial of switching Donepezil to morning dosing may help."
            ),
            urgency_level=UrgencyLevel.routine,
            recommended_actions=[
                {"action": "Ask Dr. Osei about switching Donepezil to morning dosing"},
                {"action": "Establish consistent sleep schedule; avoid screens after 8 PM"},
                {"action": "Evaluate for pain or urinary frequency as waking triggers"},
            ],
            status=EpisodeStatus.open,
        ),
    ]

    return {
        "caregiver": Caregiver(
            id=ids["caregiver_id"],
            clerk_user_id=ids["caregiver_clerk_id"],
            display_name=ids["caregiver_name"],
            email=ids["caregiver_email"],
        ),
        "cr": CareRecipient(
            id=cr_id,
            caregiver_id=ids["caregiver_id"],
            display_name="Margaret Okafor",
            date_of_birth=date(1949, 9, 14),
            sex_at_birth=SexAtBirth.female,
            conditions=[
                {"name": "Hypertension", "icd10": "I10", "since": "2010"},
                {"name": "Type 2 Diabetes", "icd10": "E11", "since": "2014"},
                {"name": "Mild Cognitive Impairment", "icd10": "G31.84", "since": "2021"},
                {"name": "Hyperlipidemia", "icd10": "E78.5", "since": "2018"},
            ],
            allergies=[
                {"substance": "Codeine", "reaction": "nausea/vomiting", "severity": "moderate"},
            ],
            baseline_notes=(
                "Lives with son James. Mobile with cane. Needs reminders for medications. "
                "Enjoys crossword puzzles. Follows low-salt diet. Former teacher."
            ),
            primary_provider_name="Dr. Amara Nwosu",
            primary_provider_email="anwosu@springfield-health.org",
            primary_provider_phone="(413) 555-0211",
            emergency_contact_name="James Okafor (son)",
            emergency_contact_phone="(413) 555-0143",
            consent_basis=ConsentBasis.healthcare_proxy,
        ),
        "medications": medications,
        "vitals": vitals,
        "episodes": episodes,
    }


def _build_persona_2(ids: dict) -> dict:
    """Robert Chen, 68M — Post-stroke recovery (ischemic stroke 2023)."""
    cr_id = ids["cr_id"]

    medications = [
        Medication(care_recipient_id=cr_id, display_name="Clopidogrel",
                   rxnorm_code="32968", rxnorm_name="Clopidogrel",
                   dose="75 mg", frequency="once daily", route="oral",
                   started_at=date(2023, 8, 20), prescribed_for="Post-stroke antiplatelet therapy",
                   prescriber="Dr. Helen Park"),
        Medication(care_recipient_id=cr_id, display_name="Aspirin",
                   rxnorm_code="1191", rxnorm_name="Aspirin",
                   dose="81 mg", frequency="once daily", route="oral",
                   started_at=date(2023, 8, 20), prescribed_for="Post-stroke antiplatelet therapy",
                   prescriber="Dr. Helen Park"),
        Medication(care_recipient_id=cr_id, display_name="Atorvastatin",
                   rxnorm_code="83367", rxnorm_name="Atorvastatin",
                   dose="80 mg", frequency="once at bedtime", route="oral",
                   started_at=date(2023, 8, 20), prescribed_for="High-intensity statin post-stroke",
                   prescriber="Dr. Helen Park"),
        Medication(care_recipient_id=cr_id, display_name="Lisinopril",
                   rxnorm_code="29046", rxnorm_name="Lisinopril",
                   dose="5 mg", frequency="once daily", route="oral",
                   started_at=date(2023, 8, 20), prescribed_for="Hypertension post-stroke",
                   prescriber="Dr. Helen Park"),
        Medication(care_recipient_id=cr_id, display_name="Amlodipine",
                   rxnorm_code="17767", rxnorm_name="Amlodipine",
                   dose="5 mg", frequency="once daily", route="oral",
                   started_at=date(2008, 7, 1), prescribed_for="Hypertension",
                   prescriber="Dr. Helen Park"),
        Medication(care_recipient_id=cr_id, display_name="Metformin",
                   rxnorm_code="6809", rxnorm_name="Metformin",
                   dose="500 mg", frequency="twice daily with meals", route="oral",
                   started_at=date(2019, 10, 1), prescribed_for="Type 2 Diabetes",
                   prescriber="Dr. Helen Park"),
    ]

    vitals = []
    for days, sys_v, dia_v in [
        (30,148,90),(27,142,86),(24,152,92),(21,138,84),(18,145,88),
        (15,140,82),(12,150,90),(9,135,80),(6,143,86),(3,147,89),(0,139,83),
    ]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.blood_pressure,
                            value_systolic=sys_v, value_diastolic=dia_v, unit="mmHg",
                            recorded_at=_ago(days), source=VitalSource.manual))

    for days, bpm in [(28,72),(22,68),(16,74),(10,70),(4,71)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.heart_rate,
                            value_numeric=bpm, unit="bpm",
                            recorded_at=_ago(days, 8, 5), source=VitalSource.manual))

    for days, val in [(26,128),(20,135),(14,131),(8,129),(2,133)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.glucose,
                            value_numeric=val, unit="mg/dL",
                            recorded_at=_ago(days, 7, 30), source=VitalSource.manual,
                            notes="Fasting"))

    for days, kg in [(28,78.4),(21,78.0),(14,77.8),(7,78.2),(0,77.9)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.weight,
                            value_numeric=kg, unit="kg",
                            recorded_at=_ago(days, 9), source=VitalSource.manual))

    episodes = [
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(18),
            caregiver_description=(
                "Dad had a headache that lasted most of the day. He also felt dizzy when "
                "he stood up quickly. BP was 148/90 this morning. He took his medications."
            ),
            symptoms=[
                {"name": "headache", "duration": "all day", "severity": "moderate"},
                {"name": "orthostatic dizziness", "onset": "standing", "severity": "mild"},
            ],
            agent_assessment=(
                "Headache and orthostatic dizziness in a post-stroke patient. BP 148/90 — "
                "above his recent baseline. Orthostatic component may be worsened by Amlodipine. "
                "Headache in a stroke survivor always warrants prompt evaluation to rule out TIA/recurrence."
            ),
            urgency_level=UrgencyLevel.same_day,
            recommended_actions=[
                {"action": "Call Dr. Park today — describe the headache and dizziness"},
                {"action": "Check BP lying, sitting, standing to quantify orthostatic drop"},
                {"action": "Do not take additional pain medications until evaluated"},
                {"action": "Watch for one-sided weakness, speech difficulty, vision change — call 911 if present"},
            ],
            status=EpisodeStatus.resolved,
            resolved_at=_ago(17),
            resolution_notes=(
                "Dr. Park evaluated. No TIA signs. BP med timing adjusted — now taking "
                "Amlodipine in the evening. Headache resolved next morning."
            ),
        ),
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(7),
            caregiver_description=(
                "Dad's left hand grip is still weaker than the right. He dropped his coffee "
                "mug today. Physical therapy is scheduled but he says his hand is 'not improving'."
            ),
            symptoms=[
                {"name": "left hand weakness", "severity": "moderate"},
                {"name": "grip loss", "side": "left", "severity": "moderate"},
            ],
            agent_assessment=(
                "Persistent left-sided weakness is consistent with incomplete motor recovery "
                "from the 2023 ischemic stroke. Dropped objects suggest fine motor impairment. "
                "PT engagement is appropriate. OT assessment for adaptive equipment may help."
            ),
            urgency_level=UrgencyLevel.routine,
            recommended_actions=[
                {"action": "Attend all PT sessions; ask therapist about hand-strengthening exercises"},
                {"action": "Request OT evaluation for grip aids and kitchen adaptations"},
                {"action": "Log grip strength progress weekly"},
                {"action": "Contact Dr. Park if weakness suddenly worsens — could signal recurrence"},
            ],
            status=EpisodeStatus.monitoring,
        ),
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(1),
            caregiver_description=(
                "Dad mentioned he's been having trouble sleeping. He wakes up around 3 AM "
                "and can't get back to sleep. His mood has been low this week."
            ),
            symptoms=[
                {"name": "insomnia", "severity": "moderate"},
                {"name": "low mood", "duration": "1 week", "severity": "mild"},
            ],
            agent_assessment=(
                "Sleep disruption and low mood post-stroke are very common — post-stroke "
                "depression affects ~30% of survivors. SSRIs have evidence for both mood and "
                "motor recovery. Worth screening formally. Sleep hygiene review also indicated."
            ),
            urgency_level=UrgencyLevel.routine,
            recommended_actions=[
                {"action": "Ask Dr. Park about depression screening (PHQ-9)"},
                {"action": "Maintain consistent sleep/wake schedule, limit daytime naps"},
                {"action": "Encourage 30-min outdoor walk daily — improves both mood and recovery"},
            ],
            status=EpisodeStatus.open,
        ),
    ]

    return {
        "caregiver": Caregiver(
            id=ids["caregiver_id"],
            clerk_user_id=ids["caregiver_clerk_id"],
            display_name=ids["caregiver_name"],
            email=ids["caregiver_email"],
        ),
        "cr": CareRecipient(
            id=cr_id,
            caregiver_id=ids["caregiver_id"],
            display_name="Robert Chen",
            date_of_birth=date(1957, 4, 22),
            sex_at_birth=SexAtBirth.male,
            conditions=[
                {"name": "Ischemic Stroke (2023)", "icd10": "I63.9", "since": "2023"},
                {"name": "Hypertension", "icd10": "I10", "since": "2008"},
                {"name": "Hyperlipidemia", "icd10": "E78.5", "since": "2016"},
                {"name": "Type 2 Diabetes", "icd10": "E11", "since": "2019"},
            ],
            allergies=[
                {"substance": "Sulfa antibiotics", "reaction": "rash", "severity": "moderate"},
            ],
            baseline_notes=(
                "Left-sided residual weakness from August 2023 ischemic stroke. In outpatient PT. "
                "Lives with daughter Linda. Retired engineer. Motivated, engaged in recovery."
            ),
            primary_provider_name="Dr. Helen Park",
            primary_provider_email="hpark@boston-neuro.org",
            primary_provider_phone="(617) 555-0342",
            emergency_contact_name="Linda Chen (daughter)",
            emergency_contact_phone="(617) 555-0278",
            consent_basis=ConsentBasis.informal_arrangement,
        ),
        "medications": medications,
        "vitals": vitals,
        "episodes": episodes,
    }


def _build_persona_3(ids: dict) -> dict:
    """Maria Santos, 54F — Stage 3B breast cancer, active treatment."""
    cr_id = ids["cr_id"]

    medications = [
        Medication(care_recipient_id=cr_id, display_name="Paclitaxel",
                   rxnorm_code="56946", rxnorm_name="Paclitaxel",
                   dose="175 mg/m²", frequency="every 3 weeks (IV infusion)", route="injection",
                   started_at=date(2023, 4, 15), prescribed_for="Breast cancer chemotherapy",
                   prescriber="Dr. Fatima Al-Rashid"),
        Medication(care_recipient_id=cr_id, display_name="Tamoxifen",
                   rxnorm_code="10324", rxnorm_name="Tamoxifen",
                   dose="20 mg", frequency="once daily", route="oral",
                   started_at=date(2024, 1, 10), prescribed_for="ER+ breast cancer hormone therapy",
                   prescriber="Dr. Fatima Al-Rashid"),
        Medication(care_recipient_id=cr_id, display_name="Ondansetron",
                   rxnorm_code="26225", rxnorm_name="Ondansetron",
                   dose="8 mg", frequency="every 8 hours as needed for nausea", route="oral",
                   started_at=date(2023, 4, 15), prescribed_for="Chemotherapy-induced nausea",
                   prescriber="Dr. Fatima Al-Rashid"),
        Medication(care_recipient_id=cr_id, display_name="Dexamethasone",
                   rxnorm_code="3264", rxnorm_name="Dexamethasone",
                   dose="8 mg", frequency="pre-chemotherapy day", route="oral",
                   started_at=date(2023, 4, 15), prescribed_for="Pre-chemotherapy antiemetic",
                   prescriber="Dr. Fatima Al-Rashid"),
        Medication(care_recipient_id=cr_id, display_name="Lorazepam",
                   rxnorm_code="6470", rxnorm_name="Lorazepam",
                   dose="0.5 mg", frequency="as needed for anxiety (max 3/day)", route="oral",
                   started_at=date(2023, 10, 5), prescribed_for="Anxiety related to cancer treatment",
                   prescriber="Dr. Fatima Al-Rashid"),
    ]

    vitals = []
    for days, bpm in [(29,88),(23,82),(17,79),(11,84),(5,81),(1,78)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.heart_rate,
                            value_numeric=bpm, unit="bpm",
                            recorded_at=_ago(days), source=VitalSource.manual))

    for days, kg in [(28,58.8),(21,58.2),(14,57.9),(7,57.5),(0,57.2)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.weight,
                            value_numeric=kg, unit="kg",
                            recorded_at=_ago(days, 9), source=VitalSource.manual,
                            notes="Weight trending down — oncology team notified"))

    for days, temp in [(25,37.1),(20,37.4),(15,36.9),(10,37.2),(5,37.0),(1,37.3)]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.temperature,
                            value_numeric=temp, unit="°C",
                            recorded_at=_ago(days, 8), source=VitalSource.manual))

    for days, sys_v, dia_v in [
        (28,112,70),(22,118,74),(16,110,68),(10,115,72),(4,113,71),(0,117,73),
    ]:
        vitals.append(Vital(care_recipient_id=cr_id, type=VitalType.blood_pressure,
                            value_systolic=sys_v, value_diastolic=dia_v, unit="mmHg",
                            recorded_at=_ago(days, 8, 10), source=VitalSource.manual))

    episodes = [
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(21),
            caregiver_description=(
                "Mom had her 8th chemo session 2 days ago. Since then she's been vomiting "
                "every few hours, can't keep water down, and hasn't eaten in 24 hours. "
                "She's taken Ondansetron but it's not controlling the nausea."
            ),
            symptoms=[
                {"name": "vomiting", "frequency": "every few hours", "severity": "severe"},
                {"name": "inability to eat", "duration": "24 hours", "severity": "severe"},
                {"name": "dehydration risk", "severity": "moderate"},
            ],
            agent_assessment=(
                "Refractory post-chemotherapy nausea/vomiting (CINV) not controlled by "
                "standard Ondansetron. Risk of dehydration. Consider IV hydration and "
                "stepped antiemetic therapy (adding Prochlorperazine or a NK1 antagonist). "
                "Oncology team should be notified today."
            ),
            urgency_level=UrgencyLevel.urgent,
            recommended_actions=[
                {"action": "Call Dr. Al-Rashid's office immediately for same-day guidance"},
                {"action": "If unable to keep any fluids down, go to infusion center for IV hydration"},
                {"action": "Small sips of clear broth / electrolyte drink every 15 min"},
                {"action": "Track fluid intake/output and report to oncology team"},
            ],
            status=EpisodeStatus.resolved,
            resolved_at=_ago(19),
            resolution_notes=(
                "Oncology nurse line directed to infusion center. IV fluids given. "
                "Added Prochlorperazine to regimen. Nausea controlled by day 3."
            ),
        ),
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(10),
            caregiver_description=(
                "Mom's feet and hands have been tingling and numb for 2 weeks now. "
                "She dropped a glass yesterday because she couldn't feel her grip. "
                "Her oncologist mentioned neuropathy was a risk."
            ),
            symptoms=[
                {"name": "peripheral tingling", "location": "hands and feet", "severity": "moderate"},
                {"name": "numbness", "location": "fingers", "severity": "moderate"},
                {"name": "reduced grip strength", "severity": "mild"},
            ],
            agent_assessment=(
                "Chemotherapy-induced peripheral neuropathy (CIPN) — expected with Paclitaxel. "
                "Dropping objects and bilateral sensory symptoms suggest grade 2 CIPN. "
                "This may warrant dose reduction or schedule change per oncology team."
            ),
            urgency_level=UrgencyLevel.same_day,
            recommended_actions=[
                {"action": "Report the severity to Dr. Al-Rashid at next visit — may require dose adjustment"},
                {"action": "Fall safety: use grab bars, non-slip mats, avoid loose rugs"},
                {"action": "Avoid extreme temperatures (hot/cold) on hands and feet — reduced sensation"},
                {"action": "Vitamin B6 supplementation only if recommended by oncologist"},
            ],
            status=EpisodeStatus.monitoring,
        ),
        Episode(
            care_recipient_id=cr_id,
            started_at=_ago(3),
            caregiver_description=(
                "Mom told me she's been feeling very anxious, especially the night before "
                "each chemo session. She's using Lorazepam more frequently (almost daily). "
                "She cried today and said she's exhausted from fighting."
            ),
            symptoms=[
                {"name": "anticipatory anxiety", "severity": "moderate"},
                {"name": "emotional distress", "severity": "moderate"},
                {"name": "fatigue", "severity": "moderate"},
            ],
            agent_assessment=(
                "Pre-treatment anxiety is common in cancer patients and can be intense before "
                "each infusion (anticipatory anxiety). Increasing Lorazepam use warrants "
                "psychiatric or social work referral. Cancer-related fatigue may also be "
                "undertreated — palliative care involvement can help."
            ),
            urgency_level=UrgencyLevel.routine,
            recommended_actions=[
                {"action": "Ask Dr. Al-Rashid for referral to oncology social worker / psycho-oncology"},
                {"action": "Discuss regular Lorazepam use with prescriber — tolerance risk"},
                {"action": "Explore non-pharmacologic approaches: guided imagery, relaxation techniques"},
                {"action": "Consider palliative care consultation for fatigue and quality of life"},
            ],
            status=EpisodeStatus.open,
        ),
    ]

    return {
        "caregiver": Caregiver(
            id=ids["caregiver_id"],
            clerk_user_id=ids["caregiver_clerk_id"],
            display_name=ids["caregiver_name"],
            email=ids["caregiver_email"],
        ),
        "cr": CareRecipient(
            id=cr_id,
            caregiver_id=ids["caregiver_id"],
            display_name="Maria Santos",
            date_of_birth=date(1971, 11, 8),
            sex_at_birth=SexAtBirth.female,
            conditions=[
                {"name": "Breast Cancer Stage 3B", "icd10": "C50.911", "since": "2023"},
                {"name": "Chemotherapy-induced neuropathy", "icd10": "G62.9", "since": "2023"},
                {"name": "Cancer-related anxiety", "icd10": "F41.1", "since": "2023"},
            ],
            allergies=[
                {"substance": "Penicillin", "reaction": "anaphylaxis", "severity": "severe"},
                {"substance": "Contrast dye", "reaction": "hives", "severity": "moderate"},
            ],
            baseline_notes=(
                "Single mother, 2 adult children. Currently on 8th cycle of Paclitaxel. "
                "Surgery (lumpectomy + sentinel node biopsy) completed Nov 2023. "
                "Transitioning to Tamoxifen maintenance. Works part-time remote when well enough."
            ),
            primary_provider_name="Dr. Fatima Al-Rashid",
            primary_provider_email="falrashid@camb-oncology.org",
            primary_provider_phone="(617) 555-0489",
            emergency_contact_name="Carlos Santos (brother)",
            emergency_contact_phone="(617) 555-0322",
            consent_basis=ConsentBasis.informal_arrangement,
        ),
        "medications": medications,
        "vitals": vitals,
        "episodes": episodes,
    }


_BUILDERS = {1: _build_persona_1, 2: _build_persona_2, 3: _build_persona_3}


async def _seed_one(
    persona_num: int,
    drop: bool = False,
    caregiver_id_override: uuid.UUID | None = None,
) -> None:
    ids = PERSONAS[persona_num]
    data = _BUILDERS[persona_num](ids)
    caregiver = data["caregiver"]
    cr = data["cr"]

    async with async_session_maker() as db:
        cr_id = ids["cr_id"]
        # Use the override (real logged-in user) or the synthetic caregiver
        cg_id = caregiver_id_override or ids["caregiver_id"]

        if drop:
            await db.execute(text("DELETE FROM episodes   WHERE care_recipient_id = :id"), {"id": cr_id})
            await db.execute(text("DELETE FROM vitals     WHERE care_recipient_id = :id"), {"id": cr_id})
            await db.execute(text("DELETE FROM medications WHERE care_recipient_id = :id"), {"id": cr_id})
            await db.execute(text("DELETE FROM care_recipients WHERE id = :id"), {"id": cr_id})
            if not caregiver_id_override:
                await db.execute(text("DELETE FROM caregivers WHERE id = :id"), {"id": cg_id})

        # Only upsert caregiver when using the synthetic ID (not the real user's account)
        if not caregiver_id_override:
            await db.execute(text("""
                INSERT INTO caregivers (id, clerk_user_id, display_name, email, timezone)
                VALUES (:id, :clerk_user_id, :display_name, :email, 'America/New_York')
                ON CONFLICT (id) DO UPDATE
                  SET display_name = EXCLUDED.display_name,
                      email        = EXCLUDED.email
            """), {
                "id": cg_id,
                "clerk_user_id": caregiver.clerk_user_id,
                "display_name": caregiver.display_name,
                "email": caregiver.email,
            })

        import json as _json
        # Upsert care recipient — use CAST(... AS jsonb) to avoid ::jsonb conflicting with SQLAlchemy param parser
        await db.execute(text("""
            INSERT INTO care_recipients
              (id, caregiver_id, display_name, date_of_birth, sex_at_birth,
               conditions, allergies, baseline_notes,
               primary_provider_name, primary_provider_email, primary_provider_phone,
               emergency_contact_name, emergency_contact_phone, consent_basis)
            VALUES
              (:id, :caregiver_id, :display_name, :dob, :sex,
               CAST(:conditions AS jsonb), CAST(:allergies AS jsonb), :baseline_notes,
               :ppn, :ppe, :ppp, :ecn, :ecp, :consent)
            ON CONFLICT (id) DO UPDATE
              SET display_name = EXCLUDED.display_name,
                  conditions   = EXCLUDED.conditions,
                  allergies    = EXCLUDED.allergies,
                  baseline_notes = EXCLUDED.baseline_notes
        """), {
            "id": cr_id,
            "caregiver_id": cg_id,
            "display_name": cr.display_name,
            "dob": cr.date_of_birth,
            "sex": cr.sex_at_birth.value,
            "conditions": _json.dumps(cr.conditions),
            "allergies": _json.dumps(cr.allergies),
            "baseline_notes": cr.baseline_notes,
            "ppn": cr.primary_provider_name,
            "ppe": cr.primary_provider_email,
            "ppp": cr.primary_provider_phone,
            "ecn": cr.emergency_contact_name,
            "ecp": cr.emergency_contact_phone,
            "consent": cr.consent_basis.value,
        })

        # Clear and re-seed linked data
        await db.execute(text("DELETE FROM medications WHERE care_recipient_id = :id"), {"id": cr_id})
        await db.execute(text("DELETE FROM vitals WHERE care_recipient_id = :id"), {"id": cr_id})
        await db.execute(text("DELETE FROM episodes WHERE care_recipient_id = :id"), {"id": cr_id})

        for obj in data["medications"] + data["vitals"] + data["episodes"]:
            db.add(obj)

        await db.commit()

    counts = {
        "meds": len(data["medications"]),
        "vitals": len(data["vitals"]),
        "episodes": len(data["episodes"]),
    }
    caregiver_label = f"your account ({cg_id})" if caregiver_id_override else caregiver.display_name
    print(
        f"  [v] Persona {persona_num}: {cr.display_name}  "
        f"({counts['meds']} meds, {counts['vitals']} vitals, {counts['episodes']} episodes)"
    )
    print(f"      Caregiver: {caregiver_label}")
    print(f"      Care recipient ID: {cr_id}")


async def main(
    persona_nums: list[int] | None = None,
    drop: bool = False,
    caregiver_id: uuid.UUID | None = None,
) -> None:
    targets = persona_nums or [1, 2, 3]
    if caregiver_id:
        print(f"Linking to caregiver {caregiver_id} (your account)")
    print(f"Seeding {len(targets)} persona(s)...")
    for n in targets:
        await _seed_one(n, drop=drop, caregiver_id_override=caregiver_id)
    print("\nDone.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=int, choices=[1, 2, 3], default=None,
                        help="Which persona to seed (default: all three)")
    parser.add_argument("--drop", action="store_true",
                        help="Delete existing records before re-seeding")
    parser.add_argument("--caregiver-id", default=None,
                        help="Link personas to this caregiver UUID (your real account) so they appear in the UI")
    args = parser.parse_args()
    asyncio.run(main(
        persona_nums=[args.persona] if args.persona else None,
        drop=args.drop,
        caregiver_id=uuid.UUID(args.caregiver_id) if args.caregiver_id else None,
    ))
