from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionIntent(StrEnum):
    THRESHOLD = "THRESHOLD"
    ANNUALIZED_INCOME = "ANNUALIZED_INCOME"
    COMPARISON = "COMPARISON"
    READINESS = "READINESS"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"
    DOCUMENT_FRESHNESS = "DOCUMENT_FRESHNESS"
    ELIGIBILITY_REQUEST = "ELIGIBILITY_REQUEST"
    PROPERTY_AVAILABILITY = "PROPERTY_AVAILABILITY"
    GEOCODE_QUALITY = "GEOCODE_QUALITY"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    FEDERAL_ANCHOR = "FEDERAL_ANCHOR"
    CROSS_HOUSEHOLD = "CROSS_HOUSEHOLD"
    UNSUPPORTED_TRAIT = "UNSUPPORTED_TRAIT"
    UNSUPPORTED = "UNSUPPORTED"


class AnswerStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    ABSTAINED = "ABSTAINED"
    REFUSED = "REFUSED"


class RuleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    authority: Literal["official_hud", "official_federal", "hackathon_simulation"]
    effective_date: str | None = None
    text: str
    source_url: str
    source_locator: str


class Citation(BaseModel):
    """One unified citation shape for rules and document evidence.

    The organizer submission schema permits citation objects without fixing
    their inner properties. This model supplies the traceability fields needed
    by the challenge while preserving the organizer's outer `citations` array.
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = None
    authority: str | None = None
    effective_date: str | None = None
    source_url: str | None = None
    source_locator: str | None = None

    document_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None
    bbox_units: Literal["pdf_points"] | None = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value):
        if value is None:
            return value
        x1, y1, x2, y2 = value
        if not (0 <= x1 < x2 <= 612 and 0 <= y1 < y2 <= 792):
            raise ValueError("bbox must be inside the organizer's 612x792 PDF-point page")
        return value


class FormulaStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    formula: str
    result: Decimal = Field(ge=0)


class CalculationContext(BaseModel):
    """Trusted output from the deterministic calculation service."""

    model_config = ConfigDict(extra="forbid")

    household_id: str
    household_size: int = Field(ge=1)
    annualized_income: Decimal | None = Field(default=None, ge=0)
    threshold: Decimal | None = Field(default=None, ge=0)
    comparison: Literal["below_or_equal", "above", "no_frozen_threshold"] | None = None
    formula_steps: list[FormulaStep] = Field(default_factory=list)
    calculation_source: Literal["deterministic"] = "deterministic"
    rule_year: Literal[2026] = 2026
    citations: list[Citation] = Field(default_factory=list)


class ChatContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    active_household_id: str | None = None
    calculation: CalculationContext | None = None
    readiness_status: Literal["READY_TO_REVIEW", "NEEDS_REVIEW"] | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    household_id: str | None = None
    question: str = Field(min_length=1, max_length=2000)


class RuleAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AnswerStatus
    intent: QuestionIntent
    answer: str | None
    citations: list[Citation] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    next_action: str | None = None
    requires_human_review: bool = False
