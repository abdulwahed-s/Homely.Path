from __future__ import annotations

from collections import OrderedDict

from .freshness import FreshnessStatus, date_from_document, evaluate_freshness
from .reason_codes import ReasonCode, reason_definition
from .schemas import (
    ChecklistItem,
    ChecklistStatus,
    ReadinessInput,
    ReadinessResult,
    ReadinessStatus,
    ReviewReason,
)


def _add_reason(
    reasons: "OrderedDict[str, ReviewReason]",
    code: str,
    evidence_ids: list[str] | None = None,
) -> None:
    definition = reason_definition(code)
    if code in reasons:
        existing = reasons[code]
        existing.evidence_ids = sorted(set(existing.evidence_ids + (evidence_ids or [])))
        return
    reasons[code] = ReviewReason(
        code=code,
        message=definition.message,
        evidence_ids=evidence_ids or [],
        blocks_readiness=definition.blocks_readiness,
        next_action=definition.next_action,
    )


def evaluate_readiness(data: ReadinessInput) -> ReadinessResult:
    reasons: "OrderedDict[str, ReviewReason]" = OrderedDict()

    for conflict in data.conflicts:
        if conflict.status != "UNRESOLVED":
            continue
        code = conflict.conflict_type
        if code not in {item.value for item in ReasonCode}:
            code = ReasonCode.UNRESOLVED_CONFLICT.value
        _add_reason(reasons, code, conflict.evidence_ids)

    for code in data.evidence_gaps:
        _add_reason(reasons, code)

    if data.unconfirmed_used_fields:
        _add_reason(
            reasons,
            ReasonCode.UNCONFIRMED_REQUIRED_FIELD.value,
            data.unconfirmed_used_fields,
        )

    # The organizer gold cases specifically treat an uploaded expired
    # employment letter as a blocking issue. Missing employment letters do not
    # automatically fail when sufficient alternative evidence exists.
    expired_letters: list[str] = []
    for document in data.documents:
        if document.document_type != "employment_letter":
            continue
        freshness = evaluate_freshness(date_from_document(document))
        if freshness.status == FreshnessStatus.EXPIRED:
            expired_letters.append(document.document_id)
    if expired_letters:
        _add_reason(reasons, ReasonCode.EMPLOYMENT_LETTER_EXPIRED.value, expired_letters)

    if (
        data.calculation_result.comparison == "no_frozen_threshold"
        or data.calculation_result.threshold is None
    ):
        _add_reason(reasons, ReasonCode.NO_FROZEN_THRESHOLD.value)

    if not data.material_citations_valid or not data.calculation_result.citations:
        _add_reason(reasons, ReasonCode.MISSING_CITATION.value)

    blocking = [reason for reason in reasons.values() if reason.blocks_readiness]
    status = (
        ReadinessStatus.NEEDS_REVIEW
        if blocking
        else ReadinessStatus.READY_TO_REVIEW
    )

    checklist = [
        ChecklistItem(
            item_id="confirmed_inputs",
            label="Values used in the calculation are renter-confirmed",
            status=(
                ChecklistStatus.NEEDS_REVIEW
                if data.unconfirmed_used_fields
                else ChecklistStatus.COMPLETE
            ),
            reason=(
                "Some calculation inputs are unconfirmed."
                if data.unconfirmed_used_fields
                else "All used values are confirmed."
            ),
            evidence_ids=data.unconfirmed_used_fields,
        ),
        ChecklistItem(
            item_id="consistent_evidence",
            label="Evidence is internally consistent",
            status=(
                ChecklistStatus.NEEDS_REVIEW
                if any(conflict.status == "UNRESOLVED" for conflict in data.conflicts)
                else ChecklistStatus.COMPLETE
            ),
            reason=(
                "At least one conflict remains unresolved."
                if any(conflict.status == "UNRESOLVED" for conflict in data.conflicts)
                else "No unresolved conflict was reported."
            ),
            evidence_ids=[
                item for conflict in data.conflicts if conflict.status == "UNRESOLVED"
                for item in conflict.evidence_ids
            ],
        ),
        ChecklistItem(
            item_id="current_evidence",
            label="Uploaded employment evidence is current under the simulation convention",
            status=(
                ChecklistStatus.NEEDS_REVIEW
                if expired_letters
                else ChecklistStatus.COMPLETE
            ),
            reason=(
                "An uploaded employment letter is older than 60 days."
                if expired_letters
                else "No expired uploaded employment letter was found."
            ),
            evidence_ids=expired_letters,
        ),
        ChecklistItem(
            item_id="frozen_threshold",
            label="A frozen threshold exists for the household size",
            status=(
                ChecklistStatus.NEEDS_REVIEW
                if data.calculation_result.threshold is None
                else ChecklistStatus.COMPLETE
            ),
            reason=(
                "No organizer threshold is supplied for this household size."
                if data.calculation_result.threshold is None
                else "The deterministic service supplied a frozen threshold."
            ),
        ),
        ChecklistItem(
            item_id="traceable_results",
            label="Material results contain document and rule citations",
            status=(
                ChecklistStatus.COMPLETE
                if data.material_citations_valid and data.calculation_result.citations
                else ChecklistStatus.NEEDS_REVIEW
            ),
            reason=(
                "Citations passed the traceability gate."
                if data.material_citations_valid and data.calculation_result.citations
                else "A required citation is missing or invalid."
            ),
        ),
    ]

    return ReadinessResult(
        household_id=data.household_id,
        annualized_income=data.calculation_result.annualized_income,
        comparison=data.calculation_result.comparison,
        readiness_status=status,
        citations=data.calculation_result.citations,
        threshold=data.calculation_result.threshold,
        formula_steps=data.calculation_result.formula_steps,
        review_reasons=list(reasons.values()),
        checklist=checklist,
        next_steps=[],  # Filled by planner/service.
    )
