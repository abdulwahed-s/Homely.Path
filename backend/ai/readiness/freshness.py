from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from .schemas import OrganizerDocument


REFERENCE_DATE = date(2026, 7, 18)
CURRENT_WINDOW_DAYS = 60


class FreshnessStatus(StrEnum):
    CURRENT = "CURRENT"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    FUTURE_DATED = "FUTURE_DATED"


@dataclass(frozen=True)
class FreshnessResult:
    status: FreshnessStatus
    age_days: int | None
    document_date: date | None


def parse_document_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None

    # ISO date.
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass

    # Common U.S. fixture formats.
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    # Statement month: treat the first day as a conservative evidence date.
    try:
        return datetime.strptime(text, "%Y-%m").date()
    except ValueError:
        return None


def evaluate_freshness(
    document_date: date | None,
    reference_date: date = REFERENCE_DATE,
) -> FreshnessResult:
    if document_date is None:
        return FreshnessResult(FreshnessStatus.UNKNOWN, None, None)
    age = (reference_date - document_date).days
    if age < 0:
        return FreshnessResult(FreshnessStatus.FUTURE_DATED, age, document_date)
    if age <= CURRENT_WINDOW_DAYS:
        return FreshnessResult(FreshnessStatus.CURRENT, age, document_date)
    return FreshnessResult(FreshnessStatus.EXPIRED, age, document_date)


def date_from_document(document: OrganizerDocument) -> date | None:
    preferred_fields = {
        "application_summary": ("application_date",),
        "pay_stub": ("pay_date", "pay_period_end"),
        "employment_letter": ("document_date",),
        "benefit_letter": ("document_date",),
        "gig_statement": ("statement_month",),
    }.get(document.document_type, ("document_date", "pay_date", "application_date"))

    values = {field.field: field.value for field in document.fields}
    for field_name in preferred_fields:
        parsed = parse_document_date(values.get(field_name))
        if parsed is not None:
            return parsed
    return None
