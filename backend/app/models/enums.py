import enum


class SexAtBirth(str, enum.Enum):
    male = "male"
    female = "female"
    intersex = "intersex"
    unknown = "unknown"


class ConsentBasis(str, enum.Enum):
    power_of_attorney = "power_of_attorney"
    healthcare_proxy = "healthcare_proxy"
    parental_responsibility = "parental_responsibility"
    informal_arrangement = "informal_arrangement"
    self = "self"


class VitalType(str, enum.Enum):
    blood_pressure = "blood_pressure"
    heart_rate = "heart_rate"
    glucose = "glucose"
    weight = "weight"
    temperature = "temperature"
    oxygen_saturation = "oxygen_saturation"
    respiratory_rate = "respiratory_rate"
    pain_score = "pain_score"


class VitalSource(str, enum.Enum):
    manual = "manual"
    device = "device"
    from_visit = "from_visit"
    from_document = "from_document"


class UrgencyLevel(str, enum.Enum):
    routine = "routine"
    same_day = "same_day"
    urgent = "urgent"
    emergency = "emergency"


class EpisodeStatus(str, enum.Enum):
    open = "open"
    monitoring = "monitoring"
    resolved = "resolved"
    escalated = "escalated"


class DocumentType(str, enum.Enum):
    lab_report = "lab_report"
    discharge_summary = "discharge_summary"
    after_visit_summary = "after_visit_summary"
    imaging_report = "imaging_report"
    prescription = "prescription"
    insurance_card = "insurance_card"
    other = "other"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"


class MessageIntent(str, enum.Enum):
    casual_chat = "casual_chat"
    vital_logging = "vital_logging"
    symptom_report = "symptom_report"
    medication_question = "medication_question"
    document_question = "document_question"
    escalation = "escalation"
    unknown = "unknown"


class VerifierSeverity(str, enum.Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"


class ProviderMessageStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    archived = "archived"
