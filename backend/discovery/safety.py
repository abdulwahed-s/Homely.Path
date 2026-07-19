"""Safety constraints for non-decisional public property discovery."""

from __future__ import annotations

from collections.abc import Iterable

FORBIDDEN_QUERY_FIELDS = frozenset(
    {
        "income",
        "renter_income",
        "eligibility",
        "eligibility_result",
        "acceptance_probability",
        "applicant_score",
        "readiness_status",
        "race",
        "religion",
        "disability",
        "family_status",
        "familial_status",
        "gender",
        "sex",
        "national_origin",
    }
)

PRIVATE_PROPERTY_FIELDS = frozenset(
    {
        "renter_name",
        "renter_email",
        "renter_income",
        "confirmed_profile",
        "uploaded_documents",
        "readiness_status",
        "exact_search_location_history",
        "session_id",
        "eligibility_result",
        "acceptance_probability",
        "race",
        "religion",
        "disability",
    }
)

PROHIBITED_DECISION_LANGUAGE = (
    "best match",
    "recommended for you",
    "likely to accept",
    "high approval chance",
    "you qualify",
    "top property",
)


def forbidden_query_fields(keys: Iterable[str]) -> list[str]:
    return sorted({key.casefold() for key in keys} & FORBIDDEN_QUERY_FIELDS)


def assert_public_property(item: dict) -> None:
    leaked = sorted(set(item) & PRIVATE_PROPERTY_FIELDS)
    if leaked:
        raise ValueError(f"private fields cannot enter discovery: {', '.join(leaked)}")


def assert_safe_response_text(text: str) -> None:
    lowered = text.casefold()
    found = [phrase for phrase in PROHIBITED_DECISION_LANGUAGE if phrase in lowered]
    if found:
        raise ValueError(f"decisional discovery language is prohibited: {found[0]}")
