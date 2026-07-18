"""
Internal Extraction Contract

Owned by: Full-stack / Integration Owner
Imported by:
- AI Developer 1
- AI Developer 2

DO NOT MODIFY AFTER CONTRACT FREEZE.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------
# ENUMS
# ---------------------------------------------------

class DocumentType(str, Enum):
    APPLICATION_SUMMARY = "application_summary"
    PAY_STUB = "pay_stub"
    EMPLOYMENT_LETTER = "employment_letter"
    BENEFIT_LETTER = "benefit_letter"
    GIG_STATEMENT = "gig_statement"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConfirmationStatus(str, Enum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    USER_EDITED = "user_edited"
    REJECTED = "rejected"


class SecurityFlag(str, Enum):
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    ADVERSARIAL_CONTENT = "adversarial_content"
    UNSUPPORTED_DOCUMENT = "unsupported_document"
    OCR_FAILURE = "ocr_failure"


class ActivityStatus(str, Enum):
    PASS = "PASS"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    WAITING = "WAITING"


# ---------------------------------------------------
# SOURCE LOCATION
# ---------------------------------------------------

class SourceBox(BaseModel):
    page: int

    x1: float
    y1: float
    x2: float
    y2: float

    source_description: str


# ---------------------------------------------------
# EXTRACTED FIELD
# ---------------------------------------------------

class ExtractedField(BaseModel):

    field_name: str

    value: Optional[str] = None

    normalized_value: Optional[float | int | str] = None

    confidence: float = Field(..., ge=0.0, le=1.0)

    confidence_level: ConfidenceLevel

    confirmation_status: ConfirmationStatus

    source: SourceBox

    requires_manual_entry: bool = False


# ---------------------------------------------------
# DOCUMENT RESULT
# ---------------------------------------------------

class DocumentExtractionResult(BaseModel):

    document_id: str

    document_type: DocumentType

    fields: List[ExtractedField]

    security_flags: List[SecurityFlag] = []


# ---------------------------------------------------
# ACTIVITY EVENTS
# ---------------------------------------------------

class ActivityEvent(BaseModel):

    timestamp: str

    agent: str

    action: str

    status: ActivityStatus

    metadata: dict = {}


# ---------------------------------------------------
# EXTRACTION RESPONSE
# ---------------------------------------------------

class ExtractionResponse(BaseModel):

    session_id: str

    document: DocumentExtractionResult

    activity_events: List[ActivityEvent]