"""CC-050: Synthea CSV importer.

Reads Synthea-generated patients.csv / conditions.csv / medications.csv
and maps the rows to our schema dicts that personas.py can insert.

Usage:
    from seed.synthea_import import load_synthea_personas
    personas = load_synthea_personas(synthea_dir="seed/synthea_data")

The returned list contains one dict per patient with keys:
    patient_id, first, last, gender, dob, conditions, medications
"""

from __future__ import annotations

import csv
import uuid
from datetime import date
from pathlib import Path

_GENDER_MAP = {"F": "female", "M": "male"}


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_synthea_personas(
    synthea_dir: str | Path = Path(__file__).parent / "synthea_data",
    patient_ids: list[str] | None = None,
) -> list[dict]:
    """Load and join Synthea CSV tables for the given patient IDs.

    If patient_ids is None, returns data for all patients in patients.csv.
    """
    base = Path(synthea_dir)
    patients = _read_csv(base / "patients.csv")
    conditions = _read_csv(base / "conditions.csv")
    medications = _read_csv(base / "medications.csv")

    # Build lookup maps keyed by Synthea patient Id
    cond_by_patient: dict[str, list[dict]] = {}
    for row in conditions:
        pid = row["PATIENT"]
        cond_by_patient.setdefault(pid, []).append({
            "icd10": row["CODE"],
            "name": row["DESCRIPTION"],
            "since": row["START"][:4] if row.get("START") else None,
        })

    med_by_patient: dict[str, list[dict]] = {}
    for row in medications:
        pid = row["PATIENT"]
        med_by_patient.setdefault(pid, []).append({
            "rxnorm_code": row["CODE"],
            "display_name": row["DESCRIPTION"].split(" MG ")[0] if " MG " in row["DESCRIPTION"] else row["DESCRIPTION"],
            "rxnorm_name": row["DESCRIPTION"],
            "dose": _extract_dose(row["DESCRIPTION"]),
            "route": _extract_route(row["DESCRIPTION"]),
            "started_at": row["START"],
            "prescribed_for": row.get("REASON_DESCRIPTION", ""),
        })

    result = []
    for p in patients:
        pid = p["Id"]
        if patient_ids and pid not in patient_ids:
            continue

        try:
            dob = date.fromisoformat(p["BIRTHDATE"])
        except (ValueError, KeyError):
            continue

        result.append({
            "synthea_id": pid,
            "first": p.get("FIRST", ""),
            "last": p.get("LAST", ""),
            "gender": _GENDER_MAP.get(p.get("GENDER", ""), "unknown"),
            "dob": dob,
            "conditions": cond_by_patient.get(pid, []),
            "medications": med_by_patient.get(pid, []),
        })

    return result


def _extract_dose(description: str) -> str:
    """Parse '40 MG' from a Synthea medication description string."""
    parts = description.split()
    for i, part in enumerate(parts):
        if part in ("MG", "MCG", "MG/ML", "UNIT") and i > 0:
            return f"{parts[i-1]} {part}"
    return ""


def _extract_route(description: str) -> str:
    desc_lower = description.lower()
    if "oral" in desc_lower:
        return "oral"
    if "inject" in desc_lower or "intravenous" in desc_lower or "iv" in desc_lower:
        return "injection"
    if "topical" in desc_lower or "cream" in desc_lower:
        return "topical"
    return "oral"


if __name__ == "__main__":
    personas = load_synthea_personas()
    for p in personas:
        print(f"\n{'='*50}")
        print(f"{p['first']} {p['last']}  ({p['gender']}, born {p['dob']})")
        print(f"  Conditions ({len(p['conditions'])}): {[c['name'] for c in p['conditions']]}")
        print(f"  Medications ({len(p['medications'])}): {[m['display_name'] for m in p['medications']]}")
