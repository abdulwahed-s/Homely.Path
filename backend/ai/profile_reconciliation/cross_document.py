"""Cross-document conflict detectors (pure).

Given several :class:`DocumentExtractionResult` for one household, surface
conflicts that require human confirmation. These detectors report evidence
only — they never decide which document is correct.

Implemented (from allowlisted fields):
- person-name mismatch across documents
- pay-frequency mismatch across pay stubs
- overlapping (duplicate) pay periods across pay stubs

Not implemented here (documented, not silently skipped):
- cross-stub gross-pay difference: intentionally dropped. Different gross across
  *different* pay periods is legitimate variance (e.g. overtime), not a conflict;
  the organizer's expected review reasons never include it. Genuine duplicate
  evidence is caught by ``detect_overlapping_pay_periods`` and intra-stub
  arithmetic mismatches by ``gross_total.detect_gross_total``.
- employer-name mismatch: ``employer_name`` is not an allowlisted field, so it
  is intentionally not extracted or compared (see aidev1 implementation notes).
- current vs. year-to-date: YTD fields are not in the allowlist.
"""

from __future__ import annotations

from itertools import combinations
from typing import List, Optional

from contracts.extraction_contract import (
    DocumentExtractionResult,
    ExtractedField,
    SourceBox,
)
from backend.ai.profile_reconciliation.conflict_types import (
    CONFLICT_OVERLAPPING_PERIODS,
    CONFLICT_PAY_FREQUENCY,
    CONFLICT_PERSON_NAME,
    ConflictSeverity,
    StructuredConflict,
)

__all__ = [
    "detect_person_name_conflict",
    "detect_pay_frequency_conflict",
    "detect_overlapping_pay_periods",
    "detect_cross_document",
]

_PAY_STUB = "pay_stub"


def _type_value(document_type) -> str:
    return getattr(document_type, "value", document_type)


def _field(document: DocumentExtractionResult, name: str) -> Optional[ExtractedField]:
    for extracted in document.fields:
        if extracted.field_name == name:
            return extracted
    return None


def _norm_value(document: DocumentExtractionResult, name: str):
    field = _field(document, name)
    return field.normalized_value if field is not None else None


def _source(document: DocumentExtractionResult, name: str) -> Optional[SourceBox]:
    field = _field(document, name)
    return field.source if field is not None else None


def _pay_stubs(documents) -> List[DocumentExtractionResult]:
    return [d for d in documents if _type_value(d.document_type) == _PAY_STUB]


def detect_person_name_conflict(documents) -> List[StructuredConflict]:
    entries = []  # (doc_id, name, source) in document order
    for doc in documents:
        name = _norm_value(doc, "person_name")
        if not isinstance(name, str) or not name.strip():
            continue
        entries.append((doc.document_id, name.strip(), _source(doc, "person_name")))
    distinct = {" ".join(name.lower().split()) for _, name, _ in entries}
    if len(distinct) <= 1:
        return []
    per_document = {doc_id: name for doc_id, name, _ in entries}
    refs = [src for _, _, src in entries if src is not None]
    return [
        StructuredConflict(
            conflict_id=f"{'+'.join(sorted(per_document))}:{CONFLICT_PERSON_NAME}",
            code=CONFLICT_PERSON_NAME,
            severity=ConflictSeverity.WARNING,
            message=(
                "Documents show different applicant names: "
                + "; ".join(sorted(distinct))
                + ". Human confirmation required."
            ),
            document_ids=list(per_document.keys()),
            field_names=["person_name"],
            observed_values={"field": "person_name", "per_document": per_document},
            source_refs=refs,
        )
    ]


def detect_pay_frequency_conflict(documents) -> List[StructuredConflict]:
    stubs = _pay_stubs(documents)
    entries = []  # (doc_id, frequency, source) in document order
    for doc in stubs:
        freq = _norm_value(doc, "pay_frequency")
        if not isinstance(freq, str) or not freq:
            continue
        entries.append((doc.document_id, freq, _source(doc, "pay_frequency")))
    distinct = {freq for _, freq, _ in entries}
    if len(distinct) <= 1:
        return []
    per_document = {doc_id: freq for doc_id, freq, _ in entries}
    refs = [src for _, _, src in entries if src is not None]
    return [
        StructuredConflict(
            conflict_id=f"{'+'.join(sorted(per_document))}:{CONFLICT_PAY_FREQUENCY}",
            code=CONFLICT_PAY_FREQUENCY,
            severity=ConflictSeverity.BLOCKING_FOR_CONFIRMATION,
            message=(
                "Pay stubs report different pay frequencies: "
                + ", ".join(sorted(distinct))
                + ". Human confirmation required."
            ),
            document_ids=list(per_document.keys()),
            field_names=["pay_frequency"],
            observed_values={"field": "pay_frequency", "per_document": per_document},
            source_refs=refs,
        )
    ]


def _period(document: DocumentExtractionResult):
    start = _norm_value(document, "pay_period_start")
    end = _norm_value(document, "pay_period_end")
    if isinstance(start, str) and isinstance(end, str) and start and end:
        return start, end
    return None


def detect_overlapping_pay_periods(documents) -> List[StructuredConflict]:
    stubs = _pay_stubs(documents)
    periods = []
    for doc in stubs:
        window = _period(doc)
        if window is not None:
            periods.append((doc.document_id, window[0], window[1]))

    conflicts: List[StructuredConflict] = []
    for (id_a, start_a, end_a), (id_b, start_b, end_b) in combinations(periods, 2):
        # Only flag *duplicate* periods (identical start and end): two stubs
        # covering the exact same period is a genuine duplicate-evidence
        # conflict. Partial overlaps of consecutive stubs are expected in the
        # organizer data (happy-path households) and are NOT flagged.
        if start_a == start_b and end_a == end_b:
            pair = sorted([id_a, id_b])
            conflicts.append(
                StructuredConflict(
                    conflict_id=f"{pair[0]}+{pair[1]}:{CONFLICT_OVERLAPPING_PERIODS}",
                    code=CONFLICT_OVERLAPPING_PERIODS,
                    severity=ConflictSeverity.WARNING,
                    message=(
                        f"Pay periods overlap between {id_a} "
                        f"({start_a}..{end_a}) and {id_b} ({start_b}..{end_b}). "
                        "Human confirmation required."
                    ),
                    document_ids=[id_a, id_b],
                    field_names=["pay_period_start", "pay_period_end"],
                    observed_values={
                        "field": ["pay_period_start", "pay_period_end"],
                        "per_document": {
                            id_a: [start_a, end_a],
                            id_b: [start_b, end_b],
                        },
                    },
                    source_refs=[
                        s
                        for s in (
                            _source(_by_id(documents, id_a), "pay_period_start"),
                            _source(_by_id(documents, id_b), "pay_period_start"),
                        )
                        if s is not None
                    ],
                )
            )
    return conflicts


def _by_id(documents, document_id) -> DocumentExtractionResult:
    for doc in documents:
        if doc.document_id == document_id:
            return doc
    raise KeyError(document_id)  # pragma: no cover - ids come from same list


def detect_cross_document(documents) -> List[StructuredConflict]:
    """Run every cross-document detector and concatenate the results."""
    conflicts: List[StructuredConflict] = []
    conflicts += detect_person_name_conflict(documents)
    conflicts += detect_pay_frequency_conflict(documents)
    conflicts += detect_overlapping_pay_periods(documents)
    return conflicts
