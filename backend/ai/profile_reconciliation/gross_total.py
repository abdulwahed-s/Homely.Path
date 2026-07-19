"""A6: pay-stub gross-total conflict detector.

Pure. For a single pay-stub document, checks whether
``regular_hours x hourly_rate`` reconciles with the displayed ``gross_pay``
within :data:`GROSS_TOLERANCE`. Reports a conflict only; it never decides which
value is correct, never annualizes, and never touches non-pay-stub documents.
"""

from typing import List, Optional

from contracts.extraction_contract import (
    DocumentExtractionResult,
    ExtractedField,
    SourceBox,
)
from backend.ai.profile_reconciliation.conflict_types import (
    CONFLICT_PAY_STUB_TOTAL,
    ConflictSeverity,
    StructuredConflict,
)
from backend.ai.profile_reconciliation.config import GROSS_TOLERANCE

__all__ = ["detect_gross_total"]

_PAY_STUB = "pay_stub"
_REQUIRED_FIELDS = ("regular_hours", "hourly_rate", "gross_pay")


def _type_value(document_type) -> str:
    return getattr(document_type, "value", document_type)


def _field(document: DocumentExtractionResult, name: str) -> Optional[ExtractedField]:
    for extracted in document.fields:
        if extracted.field_name == name:
            return extracted
    return None


def _num(extracted: Optional[ExtractedField]) -> Optional[float]:
    if extracted is None:
        return None
    value = extracted.normalized_value
    if isinstance(value, bool):  # bool is a subclass of int; reject explicitly
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _source_refs(document: DocumentExtractionResult, names) -> List[SourceBox]:
    refs: List[SourceBox] = []
    for name in names:
        extracted = _field(document, name)
        if extracted is not None and extracted.source is not None:
            refs.append(extracted.source)
    return refs


def detect_gross_total(document: DocumentExtractionResult) -> List[StructuredConflict]:
    """Return a list with at most one gross-total conflict for a pay stub.

    Returns an empty list for non-pay-stub documents, when any of
    ``regular_hours``/``hourly_rate``/``gross_pay`` is missing or non-numeric,
    or when the values reconcile within tolerance. Never raises.
    """
    if _type_value(document.document_type) != _PAY_STUB:
        return []

    hours = _num(_field(document, "regular_hours"))
    rate = _num(_field(document, "hourly_rate"))
    gross = _num(_field(document, "gross_pay"))

    if hours is None or rate is None or gross is None:
        return []

    expected = round(hours * rate, 2)
    if abs(expected - gross) <= GROSS_TOLERANCE:
        return []

    conflict = StructuredConflict(
        conflict_id=f"{document.document_id}:{CONFLICT_PAY_STUB_TOTAL}",
        code=CONFLICT_PAY_STUB_TOTAL,
        severity=ConflictSeverity.BLOCKING_FOR_CONFIRMATION,
        message=(
            f"Pay stub gross pay ({gross}) does not match regular_hours x "
            f"hourly_rate ({hours} x {rate} = {expected}). Human confirmation required."
        ),
        document_ids=[document.document_id],
        field_names=list(_REQUIRED_FIELDS),
        observed_values={
            "regular_hours": hours,
            "hourly_rate": rate,
            "gross_pay": gross,
            "expected_gross": expected,
        },
        source_refs=_source_refs(document, _REQUIRED_FIELDS),
    )
    return [conflict]
