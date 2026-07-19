from __future__ import annotations

from typing import Any

from backend.ai.readiness.schemas import ReadinessResult
from backend.ai.rules_chat.schemas import CalculationContext, RuleAnswer


def build_calculation_provenance(calculation: CalculationContext) -> dict[str, Any]:
    return {
        "result_type": "annualized_income",
        "household_id": calculation.household_id,
        "formula_steps": [step.model_dump(mode="json") for step in calculation.formula_steps],
        "calculation_source": calculation.calculation_source,
        "rule_year": calculation.rule_year,
        "citations": [citation.model_dump(mode="json", exclude_none=True) for citation in calculation.citations],
        "human_review_required": calculation.comparison == "no_frozen_threshold",
    }


def build_answer_provenance(answer: RuleAnswer) -> dict[str, Any]:
    return {
        "result_type": "rule_answer",
        "intent": answer.intent.value,
        "answer_status": answer.status.value,
        "citations": [citation.model_dump(mode="json", exclude_none=True) for citation in answer.citations],
        "human_review_required": answer.requires_human_review,
    }


def build_readiness_provenance(result: ReadinessResult) -> dict[str, Any]:
    return {
        "result_type": "readiness",
        "household_id": result.household_id,
        "readiness_status": result.readiness_status.value,
        "reason_codes": [reason.code for reason in result.review_reasons],
        "citations": [citation.model_dump(mode="json", exclude_none=True) for citation in result.citations],
        "human_review_required": result.readiness_status.value == "NEEDS_REVIEW",
    }
