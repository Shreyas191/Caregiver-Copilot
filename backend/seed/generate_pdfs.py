"""CC-051: Generate synthetic clinical PDFs for ingestion testing.

Generates 9 PDFs (3 per persona) using fpdf2.
HTML templates in seed/pdf_templates/ document the intended layout.

Output: docs/sample_data/<persona>_<type>.pdf

Usage:
    python seed/generate_pdfs.py [--output-dir <path>]
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fpdf import FPDF

_OUT_DIR = Path(__file__).parent.parent.parent.parent / "docs" / "sample_data"

# -- PDF helpers ----------------------------------------------------------------

class ClinicalPDF(FPDF):
    """Base PDF class with clinical document styling."""

    _accent: tuple[int, int, int] = (26, 58, 107)  # navy

    def __init__(self, accent: tuple[int, int, int] = (26, 58, 107)):
        super().__init__()
        self._accent = accent
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self) -> None:
        pass  # handled per-document

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, "SYNTHETIC DATA - Caregiver Co-Pilot Demonstration | NOT REAL PATIENT INFORMATION", 0, 0, "C")

    def institution_header(self, name: str, address: str, doc_type: str) -> None:
        r, g, b = self._accent
        self.set_fill_color(r, g, b)
        self.rect(20, 15, 170, 1, "F")
        self.set_xy(20, 17)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(r, g, b)
        self.cell(0, 8, name, 0, 1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, address, 0, 1)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(50, 50, 50)
        self.cell(0, 7, doc_type, 0, 1)
        self.set_fill_color(r, g, b)
        self.rect(20, self.get_y(), 170, 0.5, "F")
        self.ln(3)

    def patient_box(self, rows: list[tuple[str, str, str, str]]) -> None:
        r, g, b = self._accent
        self.set_fill_color(240, 244, 255)
        self.set_draw_color(180, 200, 230)
        x0, y0 = self.get_x(), self.get_y()
        box_h = len(rows) * 7 + 4
        self.rect(20, y0, 170, box_h, "FD")
        self.set_xy(22, y0 + 2)
        for label1, val1, label2, val2 in rows:
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(r, g, b)
            self.cell(35, 6, label1, 0, 0)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(30, 30, 30)
            self.cell(50, 6, val1, 0, 0)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(r, g, b)
            self.cell(30, 6, label2, 0, 0)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(30, 30, 30)
            self.cell(0, 6, val2, 0, 1)
            self.set_x(22)
        self.ln(3)

    def section_heading(self, title: str) -> None:
        r, g, b = self._accent
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(r, g, b)
        self.cell(0, 7, title, 0, 1)
        self.set_draw_color(r, g, b)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(2)
        self.set_text_color(30, 30, 30)
        self.set_line_width(0.2)

    def body_text(self, text: str) -> None:
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet_list(self, items: list[str]) -> None:
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        for item in items:
            self.set_x(24)
            self.cell(5, 5.5, "-", 0, 0)
            self.multi_cell(0, 5.5, item)
        self.ln(2)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> None:
        r, g, b = self._accent
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, h, 0, 0, "L", True)
        self.ln()
        fill = False
        for row in rows:
            self.set_fill_color(248, 248, 248) if fill else self.set_fill_color(255, 255, 255)
            self.set_text_color(30, 30, 30)
            self.set_font("Helvetica", "", 9)
            for cell, w in zip(row, col_widths):
                self.cell(w, 6.5, str(cell), 0, 0, "L", True)
            self.ln()
            fill = not fill
        self.ln(3)


# -- Persona data ----------------------------------------------------------------

def _dt(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


MARGARET = {
    "name": "Margaret Okafor",
    "mrn": "MRN-2024-00871",
    "dob": "1949-09-14",
    "age_sex": "76F",
    "provider": "Dr. Amara Nwosu, MD",
    "practice": "Springfield Internal Medicine",
    "address": "221 Main St Suite 400, Springfield, MA 01103  |  Tel: (413) 555-0211",
}

ROBERT = {
    "name": "Robert Chen",
    "mrn": "MRN-2024-01132",
    "dob": "1957-04-22",
    "age_sex": "68M",
    "provider": "Dr. Helen Park, MD (Neurology)",
    "practice": "Boston Neurology Associates",
    "address": "75 Harbor View Dr Suite 12, Boston, MA 02108  |  Tel: (617) 555-0342",
}

MARIA = {
    "name": "Maria Santos",
    "mrn": "MRN-2024-01477",
    "dob": "1971-11-08",
    "age_sex": "54F",
    "provider": "Dr. Fatima Al-Rashid, MD (Oncology)",
    "practice": "Cambridge Oncology Center",
    "address": "301 Maple St Suite 8, Cambridge, MA 02139  |  Tel: (617) 555-0489",
}


# -- Document generators --------------------------------------------------------

def gen_lab_report_margaret(out_path: Path) -> None:
    p = ClinicalPDF(accent=(0, 102, 51))  # green
    p.add_page()
    p.institution_header("Springfield Regional Laboratory", "45 Lab Way, Springfield, MA | CLIA: 22D0987654", "LABORATORY REPORT")
    m = MARGARET
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Ordered by:", m["provider"], "Specimen Date:", _dt(5)),
        ("Collection:", "07:32", "Report Date:", _dt(5)),
    ])

    p.section_heading("BASIC METABOLIC PANEL")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["Sodium", "138", "", "136-145", "mEq/L"],
            ["Potassium", "4.1", "", "3.5-5.1", "mEq/L"],
            ["Chloride", "101", "", "98-107", "mEq/L"],
            ["CO2 (Bicarbonate)", "24", "", "22-29", "mEq/L"],
            ["BUN", "19", "", "7-25", "mg/dL"],
            ["Creatinine", "0.92", "", "0.5-1.1", "mg/dL"],
            ["eGFR", "72", "", ">60", "mL/min/1.73m²"],
            ["Glucose (fasting)", "148", "H", "70-99", "mg/dL"],
            ["Calcium", "9.4", "", "8.5-10.5", "mg/dL"],
        ],
        [62, 22, 14, 48, 24],
    )

    p.section_heading("HEMOGLOBIN A1c")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["Hemoglobin A1c", "7.8", "H", "<7.0 (target for T2DM)", "%"],
            ["Estimated Average Glucose", "177", "H", "<154 (A1c <7%)", "mg/dL"],
        ],
        [62, 22, 14, 70, 22],
    )

    p.section_heading("COMPLETE BLOOD COUNT")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["WBC", "6.8", "", "4.5-11.0", "K/uL"],
            ["RBC", "4.1", "", "3.8-5.2", "M/uL"],
            ["Hemoglobin", "12.4", "L", "12.0-16.0", "g/dL"],
            ["Hematocrit", "36.8", "", "36.0-46.0", "%"],
            ["MCV", "82", "", "80-100", "fL"],
            ["Platelets", "224", "", "150-400", "K/uL"],
        ],
        [62, 22, 14, 48, 24],
    )

    p.section_heading("INTERPRETATION")
    p.body_text(
        "Elevated fasting glucose (148 mg/dL) and HbA1c (7.8%) indicate suboptimal glycemic control "
        "in the context of known T2DM. HbA1c has risen from 7.2% (6 months ago). Consider medication "
        "review and dietary counseling. Mild anemia (Hgb 12.4) - nutritional or chronic disease etiology; "
        "recommend iron studies at next visit. Renal function stable (eGFR 72)."
    )

    p.output(str(out_path))


def gen_after_visit_margaret(out_path: Path) -> None:
    p = ClinicalPDF(accent=(91, 45, 142))  # purple
    p.add_page()
    p.institution_header(MARGARET["practice"], MARGARET["address"], "AFTER-VISIT SUMMARY")
    m = MARGARET
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Visit Date:", _dt(9), "Provider:", m["provider"]),
        ("Visit Type:", "Follow-up - Diabetes & Cognitive Decline", "", ""),
    ])

    p.section_heading("REASON FOR VISIT")
    p.body_text("Quarterly diabetes follow-up. Caregiver reports increasing memory lapses over past 3 weeks, including episode of leaving stove on and confusion about medications.")

    p.section_heading("VITALS")
    p.table(
        ["BP", "HR", "Temp", "Weight", "O2 Sat", "BMI"],
        [["156/93 mmHg", "76 bpm", "36.8°C", "64.1 kg", "97%", "24.1 kg/m²"]],
        [32, 22, 22, 22, 22, 30],
    )

    p.section_heading("ASSESSMENT")
    p.bullet_list([
        "Type 2 Diabetes (E11) - suboptimally controlled; HbA1c 7.8% (target <7.0%)",
        "Hypertension (I10) - mild elevation today; continue current regimen",
        "Mild Cognitive Impairment (G31.84) - caregiver reports increasing lapses; Donepezil dose appropriate",
        "Hyperlipidemia (E78.5) - stable on Atorvastatin",
    ])

    p.section_heading("PLAN")
    p.bullet_list([
        "Increase Metformin to 1000 mg twice daily (from 500 mg) - titrate over 2 weeks",
        "Order repeat HbA1c in 3 months",
        "Neurology referral for formal cognitive reassessment (MoCA score 24/30 today)",
        "Home safety review: pill organizer, stove auto-shutoff, caregiver check-ins",
        "Return in 3 months or sooner if glucose consistently >180 mg/dL",
    ])

    p.section_heading("CURRENT MEDICATIONS")
    p.table(
        ["Medication", "Dose & Frequency", "For"],
        [
            ["Lisinopril", "10 mg once daily", "Hypertension"],
            ["Metformin", "500 mg BID (increasing to 1000 mg BID)", "T2DM"],
            ["Donepezil", "5 mg at bedtime", "Mild cognitive impairment"],
            ["Atorvastatin", "20 mg at bedtime", "Hyperlipidemia"],
            ["Aspirin", "81 mg once daily", "Cardiovascular prevention"],
        ],
        [55, 70, 45],
    )

    p.section_heading("NOTE FOR CAREGIVER (James Okafor)")
    p.body_text(
        "Watch for signs of Metformin GI upset as dose increases - take with meals. "
        "If Margaret seems confused, has difficulty speaking, or shows sudden personality changes, "
        "call 911 or go to the ER immediately. Install a pill organizer and consider a smart stove knob. "
        "Neurology appointment letter will arrive by mail within 5 business days."
    )
    p.output(str(out_path))


def gen_discharge_margaret(out_path: Path) -> None:
    p = ClinicalPDF(accent=(26, 58, 107))
    p.add_page()
    p.institution_header("Springfield General Hospital", "500 Hospital Drive, Springfield, MA 01104  |  Tel: (413) 555-0100", "DISCHARGE SUMMARY")
    m = MARGARET
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Admitted:", _dt(24), "Discharged:", _dt(22)),
        ("Service:", "General Internal Medicine", "Attending:", m["provider"]),
    ])

    p.section_heading("REASON FOR ADMISSION")
    p.body_text("76-year-old female with T2DM, hypertension, and mild cognitive impairment admitted for acute confusion and near-fall at home. Caregiver (son) reported finding patient disoriented in kitchen with stove on.")

    p.section_heading("HOSPITAL COURSE")
    p.body_text(
        "CT head on admission showed no acute intracranial pathology. EEG unremarkable. "
        "Confusion resolved within 12 hours. Blood glucose on admission was 312 mg/dL - "
        "likely cause of acute delirium superimposed on baseline MCI. Insulin sliding scale "
        "initiated. Nephrology consulted for eGFR 58 (acute on chronic). Discharged day 3 "
        "after glucose stabilized at 140-160 range. Social work evaluation completed; "
        "home care aide 3x/week arranged."
    )

    p.section_heading("SIGNIFICANT FINDINGS")
    p.table(
        ["Finding", "Admission", "Discharge"],
        [
            ["Blood Glucose", "312 mg/dL", "148 mg/dL"],
            ["BUN/Creatinine", "28 / 1.2", "19 / 0.92"],
            ["eGFR", "58", "72"],
            ["Blood Pressure", "168/101 mmHg", "152/90 mmHg"],
            ["CT Head", "No acute findings", "-"],
        ],
        [80, 45, 45],
    )

    p.section_heading("DISCHARGE MEDICATIONS")
    p.table(
        ["Medication", "Dose", "Frequency", "Change"],
        [
            ["Lisinopril", "10 mg", "Once daily", "No change"],
            ["Metformin", "500 mg", "Twice daily with meals", "Dose held during admission; resume"],
            ["Donepezil", "5 mg", "At bedtime", "No change"],
            ["Atorvastatin", "20 mg", "At bedtime", "No change"],
            ["Aspirin", "81 mg", "Once daily", "No change"],
        ],
        [55, 22, 45, 48],
    )

    p.section_heading("DISCHARGE INSTRUCTIONS & FOLLOW-UP")
    p.bullet_list([
        "Follow-up with Dr. Nwosu within 5 days for glucose re-check",
        "Go to ER immediately if confusion recurs, glucose >300, or she cannot be roused",
        "Home care aide starting Monday (3x/week for medication administration and safety)",
        "Blood glucose monitoring: check fasting glucose every morning; log results",
        "Neurology consult appointment scheduled - see attached letter",
    ])

    p.output(str(out_path))


# -- Robert Chen PDFs ---------------------------------------------------------

def gen_discharge_robert(out_path: Path) -> None:
    p = ClinicalPDF(accent=(26, 58, 107))
    p.add_page()
    p.institution_header("Boston Medical Center", "1 Boston Medical Center Pl, Boston, MA 02118  |  Tel: (617) 555-0200", "DISCHARGE SUMMARY - NEUROLOGY")
    m = ROBERT
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Admitted:", "2023-08-14", "Discharged:", "2023-08-19"),
        ("Service:", "Neurology / Stroke", "Attending:", m["provider"]),
    ])

    p.section_heading("REASON FOR ADMISSION")
    p.body_text("68-year-old male with hypertension and hyperlipidemia presenting via EMS with acute onset right-sided facial droop, slurred speech, and left arm weakness beginning approximately 90 minutes prior to arrival.")

    p.section_heading("HOSPITAL COURSE")
    p.body_text(
        "NIHSS on admission: 7. MRI DWI confirmed acute ischemic infarct in the right middle cerebral "
        "artery territory. tPA administered at 2h15m from symptom onset (within 4.5-hour window). "
        "No hemorrhagic transformation on 24-hour MRI. Echocardiogram showed no cardioembolic source. "
        "Carotid duplex: mild bilateral stenosis (<30%). Started on dual antiplatelet therapy (aspirin + "
        "clopidogrel) and high-intensity atorvastatin 80 mg. PT/OT/Speech therapy consulted - mild "
        "residual left-sided weakness at discharge. HTN management optimized."
    )

    p.section_heading("NEUROLOGICAL EXAM AT DISCHARGE")
    p.table(
        ["Domain", "Findings"],
        [
            ["Mental Status", "Alert and oriented x3; speech fluent"],
            ["Cranial Nerves", "Mild residual right facial asymmetry; extraocular movements intact"],
            ["Motor", "Left grip strength 3/5; right 5/5; ambulating with PT assistance"],
            ["Sensory", "Intact to light touch and pinprick bilaterally"],
            ["NIHSS at discharge", "3 (improved from 7 on admission)"],
        ],
        [60, 110],
    )

    p.section_heading("DISCHARGE MEDICATIONS")
    p.table(
        ["Medication", "Dose", "Frequency", "Indication"],
        [
            ["Clopidogrel", "75 mg", "Once daily", "Antiplatelet - 90-day dual therapy"],
            ["Aspirin", "81 mg", "Once daily", "Antiplatelet - long-term"],
            ["Atorvastatin", "80 mg", "At bedtime", "High-intensity statin"],
            ["Lisinopril", "5 mg", "Once daily", "BP management"],
            ["Amlodipine", "5 mg", "Once daily (evening)", "BP management"],
            ["Metformin", "500 mg", "Twice daily", "T2DM"],
        ],
        [40, 22, 40, 68],
    )

    p.section_heading("FOLLOW-UP & CAREGIVER INSTRUCTIONS")
    p.bullet_list([
        "Neurology follow-up (Dr. Park) in 2 weeks - MRI brain and carotid duplex repeat",
        "Outpatient PT/OT 3x/week - focus on left-hand fine motor skills",
        "BP target: <130/80 mmHg; monitor daily, report readings >150/95",
        "CALL 911 IMMEDIATELY if: new weakness, facial droop, speech difficulty, vision change, severe headache",
        "Do NOT drive until cleared by neurology (minimum 3 months seizure-free)",
        "Low-sodium, heart-healthy diet; limit alcohol; no smoking",
    ])

    p.output(str(out_path))


def gen_lab_robert(out_path: Path) -> None:
    p = ClinicalPDF(accent=(0, 102, 51))
    p.add_page()
    p.institution_header("Boston Regional Laboratory Services", "20 Lab Row, Boston, MA 02108  |  CLIA: 22D1234567", "LABORATORY REPORT")
    m = ROBERT
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Ordered by:", m["provider"], "Specimen Date:", _dt(7)),
        ("Collection:", "08:15", "Report Date:", _dt(7)),
    ])

    p.section_heading("LIPID PANEL (FASTING)")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["Total Cholesterol", "148", "", "<200", "mg/dL"],
            ["LDL Cholesterol", "72", "", "<70 (post-stroke target)", "mg/dL"],
            ["HDL Cholesterol", "48", "L", ">40 (M)", "mg/dL"],
            ["Triglycerides", "141", "", "<150", "mg/dL"],
            ["Non-HDL Cholesterol", "100", "", "<100 (high risk)", "mg/dL"],
        ],
        [62, 22, 14, 60, 12],
    )

    p.section_heading("COAGULATION")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["PT", "12.1", "", "11.5-14.5", "seconds"],
            ["INR", "1.1", "", "0.9-1.1", ""],
            ["aPTT", "28", "", "25-35", "seconds"],
        ],
        [62, 22, 14, 48, 24],
    )

    p.section_heading("BASIC METABOLIC PANEL")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["Glucose (fasting)", "131", "H", "70-99", "mg/dL"],
            ["BUN", "16", "", "7-25", "mg/dL"],
            ["Creatinine", "0.98", "", "0.7-1.2", "mg/dL"],
            ["eGFR", "78", "", ">60", "mL/min/1.73m²"],
            ["Sodium", "139", "", "136-145", "mEq/L"],
            ["Potassium", "3.9", "", "3.5-5.1", "mEq/L"],
            ["HbA1c", "6.8", "H", "<5.7 normal / <7.0 target", "%"],
        ],
        [62, 22, 14, 60, 12],
    )

    p.section_heading("INTERPRETATION")
    p.body_text(
        "LDL 72 mg/dL - approaching post-stroke target of <70 mg/dL; high-intensity Atorvastatin 80 mg "
        "appropriate. Fasting glucose 131 and HbA1c 6.8% - T2DM near target but mildly elevated; "
        "continue current Metformin regimen. Coagulation studies normal; not on anticoagulation. "
        "Renal function adequate for current medications."
    )

    p.output(str(out_path))


def gen_after_visit_robert(out_path: Path) -> None:
    p = ClinicalPDF(accent=(91, 45, 142))
    p.add_page()
    p.institution_header(ROBERT["practice"], ROBERT["address"], "AFTER-VISIT SUMMARY - NEUROLOGY")
    m = ROBERT
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Visit Date:", _dt(14), "Provider:", m["provider"]),
        ("Visit Type:", "Post-Stroke Follow-up (3 months)", "", ""),
    ])

    p.section_heading("REASON FOR VISIT")
    p.body_text("3-month neurology follow-up post-ischemic stroke (August 2023). Caregiver reports persistent left-hand weakness and recent headache episode with orthostatic dizziness.")

    p.section_heading("VITALS")
    p.table(
        ["BP (sitting)", "BP (standing)", "HR", "Weight"],
        [["143/87 mmHg", "135/80 mmHg", "70 bpm", "78.0 kg"]],
        [40, 40, 22, 28],
    )

    p.section_heading("ASSESSMENT")
    p.bullet_list([
        "Ischemic stroke (I63.9) - ongoing recovery; motor deficits improving per PT assessment",
        "Orthostatic hypotension - Amlodipine dose timing adjusted (now evening)",
        "Post-stroke depression risk - PHQ-9 score 8 (mild); initiating monitoring",
        "T2DM - HbA1c 6.8%, adequate control",
        "Dual antiplatelet therapy (clopidogrel + aspirin) - will complete 90-day course in 2 weeks",
    ])

    p.section_heading("PLAN")
    p.bullet_list([
        "Transition to aspirin monotherapy after 90-day dual antiplatelet period (in 2 weeks)",
        "Continue PT/OT; request grip dynamometer assessment at next PT session",
        "PHQ-9 repeat in 4 weeks; if score increases, consider SSRI (citalopram)",
        "MRI brain (6-month post-stroke) - order placed; radiology will call to schedule",
        "Next neurology visit in 3 months",
    ])

    p.section_heading("NOTE FOR CAREGIVER (Linda Chen)")
    p.body_text(
        "Watch for sudden onset of weakness, speech problems, vision changes, or severe headache - "
        "these are stroke warning signs; call 911 immediately. The headache episode last month was "
        "evaluated and was NOT a stroke. BP monitoring twice daily remains important. "
        "Encourage Robert's PT exercises daily at home - consistency is key to motor recovery."
    )

    p.output(str(out_path))


# -- Maria Santos PDFs ---------------------------------------------------------

def gen_lab_maria(out_path: Path) -> None:
    p = ClinicalPDF(accent=(0, 102, 51))
    p.add_page()
    p.institution_header("Cambridge Oncology Laboratory", "301 Maple St, Cambridge, MA 02139  |  CLIA: 22D7654321", "LABORATORY REPORT - ONCOLOGY")
    m = MARIA
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Ordered by:", m["provider"], "Specimen Date:", _dt(3)),
        ("Collection:", "09:00", "Cycle / Day:", "Cycle 8 / Day 1 pre-infusion"),
    ])

    p.section_heading("COMPLETE BLOOD COUNT")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["WBC", "2.8", "L", "4.5-11.0", "K/uL"],
            ["Neutrophils (ANC)", "1.4", "L", ">1.5 (safe for chemo)", "K/uL"],
            ["Lymphocytes", "0.9", "L", "1.0-4.8", "K/uL"],
            ["Hemoglobin", "10.1", "L", "12.0-16.0", "g/dL"],
            ["Hematocrit", "30.2", "L", "36.0-46.0", "%"],
            ["Platelets", "182", "", "150-400", "K/uL"],
        ],
        [62, 22, 14, 60, 12],
    )

    p.section_heading("COMPREHENSIVE METABOLIC PANEL")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["AST", "44", "H", "10-40", "U/L"],
            ["ALT", "52", "H", "7-35", "U/L"],
            ["Alkaline Phosphatase", "88", "", "44-147", "U/L"],
            ["Total Bilirubin", "0.8", "", "0.1-1.2", "mg/dL"],
            ["Creatinine", "0.76", "", "0.5-1.1", "mg/dL"],
            ["BUN", "14", "", "7-25", "mg/dL"],
            ["Sodium", "138", "", "136-145", "mEq/L"],
            ["Albumin", "3.4", "L", "3.5-5.0", "g/dL"],
        ],
        [62, 22, 14, 48, 24],
    )

    p.section_heading("TUMOR MARKERS")
    p.table(
        ["Test", "Result", "Flag", "Reference Range", "Units"],
        [
            ["CA 15-3", "28", "", "<31.3", "U/mL"],
            ["CEA", "2.1", "", "<3.0 (non-smoker)", "ng/mL"],
        ],
        [62, 22, 14, 48, 24],
    )

    p.section_heading("INTERPRETATION")
    p.body_text(
        "Mild myelosuppression: ANC 1.4 K/uL (borderline - discuss with oncologist before proceeding with Cycle 8). "
        "Mild normocytic anemia (Hgb 10.1) consistent with chemotherapy effect. "
        "Mild hepatotoxicity (elevated AST/ALT) - monitor; Paclitaxel-associated. "
        "Tumor markers CA 15-3 and CEA within normal limits - encouraging response to treatment. "
        "Low albumin (3.4) suggests nutritional depletion - nutritional consultation recommended."
    )

    p.output(str(out_path))


def gen_after_visit_maria(out_path: Path) -> None:
    p = ClinicalPDF(accent=(91, 45, 142))
    p.add_page()
    p.institution_header(MARIA["practice"], MARIA["address"], "AFTER-VISIT SUMMARY - ONCOLOGY")
    m = MARIA
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Visit Date:", _dt(3), "Provider:", m["provider"]),
        ("Visit Type:", "Cycle 8 Pre-Infusion Assessment - Paclitaxel", "", ""),
    ])

    p.section_heading("REASON FOR VISIT")
    p.body_text("Pre-chemotherapy assessment for Cycle 8. Patient reports worsening peripheral neuropathy (feet/hands tingling), increased anxiety, and weight loss of 1.6 kg since last cycle.")

    p.section_heading("VITALS")
    p.table(
        ["BP", "HR", "Temp", "Weight", "O2 Sat"],
        [["115/72 mmHg", "80 bpm", "37.1°C", "57.2 kg", "98%"]],
        [35, 22, 22, 25, 26],
    )

    p.section_heading("ASSESSMENT")
    p.bullet_list([
        "Breast cancer Stage 3B (C50.911) - completing adjuvant Paclitaxel; tumor markers currently normal",
        "Chemotherapy-induced peripheral neuropathy (CIPN) - Grade 2; bilateral hands and feet",
        "Chemotherapy-induced anemia - Hgb 10.1 g/dL; no transfusion needed today",
        "Mild hepatotoxicity - AST/ALT mildly elevated; monitoring",
        "Borderline ANC (1.4) - Paclitaxel Cycle 8 HELD today; repeat CBC in 5 days",
        "Cancer-related anxiety - PHQ-4 score 9; psycho-oncology referral placed",
        "Nutritional depletion - albumin 3.4; dietitian referral placed",
    ])

    p.section_heading("PLAN")
    p.bullet_list([
        "Paclitaxel Cycle 8 HELD - ANC 1.4 K/uL; repeat CBC in 5 days; reschedule if ANC >1.5",
        "CIPN: consider Paclitaxel dose reduction (15%) at next cycle given Grade 2 neuropathy",
        "Gabapentin 100 mg at bedtime for neuropathic pain - start tonight, titrate as needed",
        "Dietitian referral for malnutrition risk - high-protein supplements recommended",
        "Psycho-oncology appointment scheduled (next week) - address treatment anxiety",
        "Transition to Tamoxifen after completing Paclitaxel course (est. 2 more cycles)",
    ])

    p.section_heading("CURRENT MEDICATIONS")
    p.table(
        ["Medication", "Dose & Frequency", "Notes"],
        [
            ["Paclitaxel (IV)", "175 mg/m² q21d", "Cycle HELD today - see plan"],
            ["Tamoxifen", "20 mg daily", "Start after chemo completion"],
            ["Ondansetron", "8 mg q8h PRN", "Take 30 min before nausea onset"],
            ["Dexamethasone", "8 mg pre-chemo", "On chemo days only"],
            ["Lorazepam", "0.5 mg PRN (max 3/day)", "Use sparingly; discuss with psycho-oncology"],
            ["Gabapentin", "100 mg at bedtime", "NEW today - for CIPN neuropathic pain"],
        ],
        [50, 55, 65],
    )

    p.section_heading("NOTE FOR CAREGIVER (Carlos Santos)")
    p.body_text(
        "Chemo was postponed today - Maria's blood counts are too low to proceed safely. "
        "This is common and does NOT mean the cancer is progressing. Bring her back in 5 days for "
        "repeat blood work. Watch for fever >38°C or chills - go to the ER immediately (neutropenic fever). "
        "Encourage protein-rich foods (eggs, yogurt, chicken) to help rebuild her strength. "
        "The new foot/hand tingling is a known chemo side effect; the new medication (Gabapentin) "
        "should help. Contact us anytime at (617) 555-0489."
    )

    p.output(str(out_path))


def gen_discharge_maria(out_path: Path) -> None:
    p = ClinicalPDF(accent=(26, 58, 107))
    p.add_page()
    p.institution_header("Cambridge Oncology Infusion Center", "301 Maple St, Cambridge, MA 02139  |  Tel: (617) 555-0489", "INFUSION CENTER DISCHARGE NOTE")
    m = MARIA
    p.patient_box([
        ("Patient:", m["name"], "MRN:", m["mrn"]),
        ("DOB:", m["dob"], "Age/Sex:", m["age_sex"]),
        ("Infusion Date:", _dt(21), "Discharge:", _dt(21)),
        ("Service:", "Oncology Infusion", "RN:", "Amanda Torres, RN OCN"),
    ])

    p.section_heading("REASON FOR VISIT")
    p.body_text("Patient presented for Cycle 7 Paclitaxel infusion. Developed refractory nausea/vomiting 48 hours post-infusion with inability to maintain oral hydration. Presented to infusion center for IV fluid resuscitation and antiemetic management.")

    p.section_heading("CLINICAL COURSE")
    p.body_text(
        "Patient received 1L NS IV over 2 hours. IV Ondansetron 4 mg administered x2 (q4h). "
        "IV Prochlorperazine 10 mg administered once. Nausea resolved after second antiemetic dose. "
        "Oral fluids tolerated before discharge. Oral medications reviewed with patient and caregiver. "
        "Patient discharged in stable condition after 4 hours. Prochlorperazine added to oral regimen."
    )

    p.section_heading("VITAL SIGNS DURING VISIT")
    p.table(
        ["Time", "BP", "HR", "Temp", "O2 Sat", "Weight"],
        [
            ["Arrival (09:30)", "108/68 mmHg", "94 bpm", "37.0°C", "97%", "56.8 kg"],
            ["Post-hydration (11:30)", "116/74 mmHg", "82 bpm", "37.1°C", "98%", "-"],
            ["Discharge (13:30)", "118/76 mmHg", "79 bpm", "36.9°C", "99%", "-"],
        ],
        [40, 35, 22, 22, 22, 29],
    )

    p.section_heading("DISCHARGE MEDICATIONS (ADDITIONS)")
    p.table(
        ["Medication", "Dose", "Frequency", "Duration"],
        [
            ["Prochlorperazine (NEW)", "10 mg", "Every 6 hours for 48h", "2 days post-chemo"],
            ["Ondansetron", "8 mg", "Every 8 hours PRN", "Continue as before"],
        ],
        [55, 22, 55, 38],
    )

    p.section_heading("DISCHARGE INSTRUCTIONS")
    p.bullet_list([
        "Small, frequent sips of clear liquids for 6 hours; advance to soft foods as tolerated",
        "Take Prochlorperazine on schedule for 48 hours after chemo, then as needed",
        "Return IMMEDIATELY for: fever >38°C, inability to keep fluids down for >8 hours, "
        "severe abdominal pain, or signs of bleeding",
        "Oncology follow-up: pre-Cycle 8 labs in 14 days",
        "Call (617) 555-0489 with any concerns (24-hour nurse line available)",
    ])

    p.output(str(out_path))


# -- Main ------------------------------------------------------------------------

def generate_all(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        ("margaret_okafor_lab_report.pdf", gen_lab_report_margaret),
        ("margaret_okafor_after_visit_summary.pdf", gen_after_visit_margaret),
        ("margaret_okafor_discharge_summary.pdf", gen_discharge_margaret),
        ("robert_chen_discharge_summary.pdf", gen_discharge_robert),
        ("robert_chen_lab_report.pdf", gen_lab_robert),
        ("robert_chen_after_visit_summary.pdf", gen_after_visit_robert),
        ("maria_santos_lab_report.pdf", gen_lab_maria),
        ("maria_santos_after_visit_summary.pdf", gen_after_visit_maria),
        ("maria_santos_discharge_summary.pdf", gen_discharge_maria),
    ]

    generated = []
    for filename, fn in tasks:
        path = output_dir / filename
        fn(path)
        generated.append(path)
        print(f"  [v] {filename}")

    return generated


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(_OUT_DIR))
    args = parser.parse_args()

    out = Path(args.output_dir)
    print(f"Generating 9 clinical PDFs -> {out}/")
    paths = generate_all(out)
    print(f"\n[OK] Done. {len(paths)} PDFs written.")
