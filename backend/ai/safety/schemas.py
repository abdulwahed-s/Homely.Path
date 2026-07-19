from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from backend.ai.rules_chat.schemas import Citation


class SafetyStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class SafetyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_text: str = ""
    response_text: str = ""
    citations: list[Citation] = Field(default_factory=list)
    active_household_id: str | None = None
    referenced_household_ids: list[str] = Field(default_factory=list)
    calculation_source: str | None = None
    readiness_status: str | None = None
    unconfirmed_values_labelled: bool = True
    claims_current_property_availability: bool = False


class SafetyChecks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisioning_claim_present: bool = False
    applicant_score_or_ranking_present: bool = False
    protected_trait_inference_present: bool = False
    cross_household_data_present: bool = False
    missing_material_citation: bool = False
    non_deterministic_calculation_present: bool = False
    unconfirmed_values_unlabelled: bool = False
    invalid_readiness_status: bool = False
    property_availability_claim_present: bool = False


class SafetyValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SafetyStatus
    safe_to_display: bool
    checks: SafetyChecks
    violations: list[str] = Field(default_factory=list)
    replacement_message: str | None = None
