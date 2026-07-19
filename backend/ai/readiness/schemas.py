from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.ai.rules_chat.schemas import Citation, FormulaStep


class ReadinessStatus(StrEnum):
    READY_TO_REVIEW = "READY_TO_REVIEW"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ChecklistStatus(StrEnum):
    COMPLETE = "COMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OrganizerField(BaseModel):
    """Mirrors fields in `document_gold.schema.json` without renaming them."""

    model_config = ConfigDict(extra="allow")

    field: str
    value: Any
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    bbox_units: Literal["pdf_points"] = "pdf_points"

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value):
        x1, y1, x2, y2 = value
        if not (0 <= x1 < x2 <= 612 and 0 <= y1 < y2 <= 792):
            raise ValueError("bbox must be inside the organizer's 612x792 page")
        return value


class OrganizerDocument(BaseModel):
    """Directly follows the organizer document extraction schema."""

    model_config = ConfigDict(extra="allow")

    document_id: str
    household_id: str
    document_type: str
    file_name: str
    synthetic: bool = True
    fields: list[OrganizerField]


class Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    conflict_type: str
    status: Literal["UNRESOLVED", "RESOLVED"]
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str | None = None


class CalculationResult(BaseModel):
    """Trusted result from deterministic backend code.

    Its core fields are the same values required by the organizer submission
    schema. Readiness adds the final `readiness_status` later.
    """

    model_config = ConfigDict(extra="forbid")

    household_id: str
    household_size: int = Field(ge=1)
    annualized_income: Decimal = Field(ge=0)
    threshold: Decimal | None = Field(default=None, ge=0)
    comparison: Literal["below_or_equal", "above", "no_frozen_threshold"]
    formula_steps: list[FormulaStep] = Field(default_factory=list)
    calculation_source: Literal["deterministic"] = "deterministic"
    rule_year: Literal[2026] = 2026
    citations: list[Citation] = Field(default_factory=list)


class ReadinessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    household_id: str
    documents: list[OrganizerDocument]
    calculation_result: CalculationResult

    # Supplied by AI Developer 1 / integration after reconciliation.
    conflicts: list[Conflict] = Field(default_factory=list)

    # Exact organizer-compatible review codes not represented in the extraction
    # schema, e.g. GIG_INCOME_UNCORROBORATED.
    evidence_gaps: list[str] = Field(default_factory=list)

    # IDs such as "HH-001-D02:gross_pay" for values actually used in the
    # calculation but not yet renter-confirmed.
    unconfirmed_used_fields: list[str] = Field(default_factory=list)

    # Final traceability gate supplied by integration after checking document
    # and rule citations.
    material_citations_valid: bool = True

    @model_validator(mode="after")
    def household_ids_must_match(self):
        if self.calculation_result.household_id != self.household_id:
            raise ValueError("Calculation result household_id does not match readiness input")
        mismatches = [doc.document_id for doc in self.documents if doc.household_id != self.household_id]
        if mismatches:
            raise ValueError(f"Documents from another household are not allowed: {mismatches}")
        return self


class ReviewReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)
    blocks_readiness: bool = True
    next_action: str | None = None


class ChecklistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    label: str
    status: ChecklistStatus
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class NextStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    action: str
    action_type: Literal["USER_REQUIRED", "AUTOMATIC", "HUMAN_REVIEW"]


class ReadinessResult(BaseModel):
    """Organizer submission fields plus UI-facing explanations."""

    model_config = ConfigDict(extra="forbid")

    household_id: str
    annualized_income: Decimal = Field(ge=0)
    comparison: Literal["below_or_equal", "above", "no_frozen_threshold"]
    readiness_status: ReadinessStatus
    citations: list[Citation]

    threshold: Decimal | None = Field(default=None, ge=0)
    formula_steps: list[FormulaStep] = Field(default_factory=list)
    review_reasons: list[ReviewReason] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)
