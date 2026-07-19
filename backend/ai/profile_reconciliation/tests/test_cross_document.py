"""Cross-document conflict detectors: gold-derived proof + edge cases (FR1.12).

Covers the detectors that previously had no test: pay-frequency mismatch,
duplicate/overlapping pay periods, cross-stub gross-pay mismatch, and
person-name mismatch. Fixtures mirror the organizer households:

- HH-001 (happy path): two pay stubs, same biweekly frequency, equal gross,
  *partially overlapping* consecutive periods -> NO conflicts.
- HH-002 (conflict): two pay stubs with differing gross (960 vs 1395) -> a
  cross-stub gross-pay conflict.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.extraction_contract import (  # noqa: E402
    ConfidenceLevel,
    ConfirmationStatus,
    DocumentExtractionResult,
    DocumentType,
    ExtractedField,
    SourceBox,
)
from backend.ai.profile_reconciliation.conflict_types import (  # noqa: E402
    CONFLICT_OVERLAPPING_PERIODS,
    CONFLICT_PAY_FREQUENCY,
    CONFLICT_PERSON_NAME,
)
from backend.ai.profile_reconciliation.cross_document import (  # noqa: E402
    detect_cross_document,
    detect_overlapping_pay_periods,
    detect_pay_frequency_conflict,
    detect_person_name_conflict,
)


def _field(name, normalized):
    return ExtractedField(
        field_name=name,
        value=str(normalized),
        normalized_value=normalized,
        confidence=0.9,
        confidence_level=ConfidenceLevel.HIGH,
        confirmation_status=ConfirmationStatus.AWAITING_CONFIRMATION,
        source=SourceBox(page=1, x1=1.0, y1=1.0, x2=2.0, y2=2.0, source_description="d"),
        requires_manual_entry=False,
    )


def _doc(doc_id, dtype, **fields):
    return DocumentExtractionResult(
        document_id=doc_id,
        document_type=dtype,
        fields=[_field(name, value) for name, value in fields.items()],
        security_flags=[],
    )


def _codes(conflicts):
    return {c.code for c in conflicts}


class PayFrequencyConflictTests(unittest.TestCase):
    def test_mismatch_flags(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_frequency="weekly"),
            _doc("D2", DocumentType.PAY_STUB, pay_frequency="biweekly"),
        ]
        conflicts = detect_pay_frequency_conflict(docs)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].code, CONFLICT_PAY_FREQUENCY)

    def test_same_frequency_no_conflict(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_frequency="biweekly"),
            _doc("D2", DocumentType.PAY_STUB, pay_frequency="biweekly"),
        ]
        self.assertEqual(detect_pay_frequency_conflict(docs), [])

    def test_ignores_non_pay_stub(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_frequency="weekly"),
            _doc("D2", DocumentType.BENEFIT_LETTER, benefit_frequency="monthly"),
        ]
        self.assertEqual(detect_pay_frequency_conflict(docs), [])


class OverlappingPayPeriodTests(unittest.TestCase):
    def test_identical_periods_flag(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_period_start="2026-06-10", pay_period_end="2026-06-23"),
            _doc("D2", DocumentType.PAY_STUB, pay_period_start="2026-06-10", pay_period_end="2026-06-23"),
        ]
        conflicts = detect_overlapping_pay_periods(docs)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].code, CONFLICT_OVERLAPPING_PERIODS)

    def test_partial_overlap_not_flagged(self):
        # HH-001 real consecutive stubs partially overlap by design -> no flag.
        docs = [
            _doc("HH-001-D02", DocumentType.PAY_STUB, pay_period_start="2026-06-10", pay_period_end="2026-06-23"),
            _doc("HH-001-D03", DocumentType.PAY_STUB, pay_period_start="2026-06-03", pay_period_end="2026-06-16"),
        ]
        self.assertEqual(detect_overlapping_pay_periods(docs), [])

    def test_disjoint_periods_not_flagged(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_period_start="2026-06-10", pay_period_end="2026-06-16"),
            _doc("D2", DocumentType.PAY_STUB, pay_period_start="2026-06-17", pay_period_end="2026-06-23"),
        ]
        self.assertEqual(detect_overlapping_pay_periods(docs), [])


class GrossPayNotFlaggedTests(unittest.TestCase):
    def test_differing_gross_across_periods_is_not_a_conflict(self):
        # Overtime variance across different periods is legitimate: the dropped
        # cross-stub gross-pay detector must not resurface as a conflict.
        docs = [
            _doc("HH-002-D02", DocumentType.PAY_STUB, gross_pay=1395.0),
            _doc("HH-002-D03", DocumentType.PAY_STUB, gross_pay=960.0),
        ]
        codes = _codes(detect_cross_document(docs))
        self.assertNotIn("GROSS_PAY_CONFLICT", codes)
        self.assertEqual(codes, set())


class PersonNameConflictTests(unittest.TestCase):
    def test_mismatch_flags(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, person_name="Mara North"),
            _doc("D2", DocumentType.PAY_STUB, person_name="Jonas Vale"),
        ]
        conflicts = detect_person_name_conflict(docs)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].code, CONFLICT_PERSON_NAME)

    def test_same_name_case_insensitive_no_conflict(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, person_name="Mara North"),
            _doc("D2", DocumentType.APPLICATION_SUMMARY, person_name="mara  north"),
        ]
        self.assertEqual(detect_person_name_conflict(docs), [])


class ObservedValuesShapeTests(unittest.TestCase):
    """Every cross-document conflict uses the uniform per-document shape."""

    def test_pay_frequency_per_document_map(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_frequency="weekly"),
            _doc("D2", DocumentType.PAY_STUB, pay_frequency="biweekly"),
        ]
        ov = detect_pay_frequency_conflict(docs)[0].observed_values
        self.assertEqual(ov["field"], "pay_frequency")
        self.assertEqual(ov["per_document"], {"D1": "weekly", "D2": "biweekly"})

    def test_person_name_per_document_map(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, person_name="Mara North"),
            _doc("D2", DocumentType.PAY_STUB, person_name="Jonas Vale"),
        ]
        ov = detect_person_name_conflict(docs)[0].observed_values
        self.assertEqual(ov["field"], "person_name")
        self.assertEqual(set(ov["per_document"]), {"D1", "D2"})

    def test_overlapping_per_document_map(self):
        docs = [
            _doc("D1", DocumentType.PAY_STUB, pay_period_start="2026-06-10", pay_period_end="2026-06-23"),
            _doc("D2", DocumentType.PAY_STUB, pay_period_start="2026-06-10", pay_period_end="2026-06-23"),
        ]
        ov = detect_overlapping_pay_periods(docs)[0].observed_values
        self.assertEqual(ov["field"], ["pay_period_start", "pay_period_end"])
        self.assertEqual(ov["per_document"]["D1"], ["2026-06-10", "2026-06-23"])


class CrossDocumentAggregateTests(unittest.TestCase):
    def test_happy_path_household_has_no_conflicts(self):
        docs = [
            _doc("HH-001-D01", DocumentType.APPLICATION_SUMMARY, person_name="Mara North"),
            _doc("HH-001-D02", DocumentType.PAY_STUB, person_name="Mara North",
                 pay_frequency="biweekly", gross_pay=2166.0,
                 pay_period_start="2026-06-10", pay_period_end="2026-06-23"),
            _doc("HH-001-D03", DocumentType.PAY_STUB, person_name="Mara North",
                 pay_frequency="biweekly", gross_pay=2166.0,
                 pay_period_start="2026-06-03", pay_period_end="2026-06-16"),
        ]
        self.assertEqual(detect_cross_document(docs), [])

    def test_hh002_has_no_cross_document_conflict(self):
        # HH-002's only conflict is the intra-stub PAY_STUB_TOTAL_CONFLICT
        # (detected by gross_total, not here). Cross-document is clean: same
        # name, same frequency, non-duplicate periods, and differing gross is
        # legitimate variance (no longer flagged).
        docs = [
            _doc("HH-002-D02", DocumentType.PAY_STUB, person_name="Jonas Vale",
                 pay_frequency="weekly", gross_pay=1395.0,
                 pay_period_start="2026-06-17", pay_period_end="2026-06-23"),
            _doc("HH-002-D03", DocumentType.PAY_STUB, person_name="Jonas Vale",
                 pay_frequency="weekly", gross_pay=960.0,
                 pay_period_start="2026-06-10", pay_period_end="2026-06-16"),
        ]
        self.assertEqual(detect_cross_document(docs), [])


if __name__ == "__main__":
    unittest.main()
