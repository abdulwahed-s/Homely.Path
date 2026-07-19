"""Build the minimum chat context from a trusted stored session result."""

from __future__ import annotations

from typing import Any

from backend.ai.rules_chat.schemas import GroundedChatContext

CALCULATION_FIELDS = {
    "household_id",
    "household_size",
    "annualized_income",
    "threshold",
    "comparison",
    "formula_steps",
    "calculation_source",
    "rule_year",
    "citations",
}
REVIEW_REASON_FIELDS = {"code", "message", "severity"}
CHECKLIST_FIELDS = {"item", "code", "status", "message", "document_id"}
CONFLICT_FIELDS = {
    "conflict_id",
    "code",
    "conflict_type",
    "status",
    "message",
    "reason",
    "document_ids",
    "field_names",
}
NEXT_STEP_FIELDS = {"code", "action", "label"}
PROPERTY_FIELDS = {
    "property_id",
    "property_name",
    "city",
    "state",
    "zip_code",
    "availability_status",
    "fmr_reference",
    "mtsp_reference",
}


def _limited_dict(value: Any, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in fields if key in value}


def _limited_list(value: Any, fields: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        limited
        for item in value
        if (limited := _limited_dict(item, fields))
    ]


def build_chat_context(session: dict[str, Any]) -> GroundedChatContext:
    """Exclude raw documents, OCR, unconfirmed values, and unrelated profiles."""
    calculation = _limited_dict(session.get("calculation"), CALCULATION_FIELDS)
    selected_property = _limited_dict(
        session.get("selected_property"), PROPERTY_FIELDS
    )
    return GroundedChatContext(
        session_id=str(session["session_id"]),
        household_id=str(session["household_id"]),
        readiness_status=session.get("readiness_status"),
        calculation=calculation or None,
        review_reasons=_limited_list(
            session.get("review_reasons"), REVIEW_REASON_FIELDS
        ),
        checklist=_limited_list(session.get("checklist"), CHECKLIST_FIELDS),
        conflicts=_limited_list(session.get("conflicts"), CONFLICT_FIELDS),
        next_steps=_limited_list(session.get("next_steps"), NEXT_STEP_FIELDS),
        selected_property=selected_property or None,
    )
