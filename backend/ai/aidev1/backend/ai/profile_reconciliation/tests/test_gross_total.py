"""A6 tests: gross-total conflict detection (gold-derived + edge cases)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.contracts.extraction_contract import (  # noqa: E402
    ConfidenceLevel,
    ConfirmationStatus,
    DocumentExtractionResult,
    DocumentType,
    ExtractedField,
    SourceBox,
)
from backend.ai.profile_reconciliation.conflict_types import (  # noqa: E402
    CONFLICT_PAY_STUB_TOTAL,
    ConflictSeverity,
)
from backend.ai.profile_reconciliation.gross_total import detect_gross_total  # noqa: E402

_ELIGIBILITY_TOKENS = ("approve", "approved", "deny", "denied", "eligible", "eligibility")


def _mk_field(name, normalized):
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


def _pay_stub(doc_id, hours=None, rate=None, gross=None, dtype=DocumentType.PAY_STUB):
    fields = []
    if hours is not None:
        fields.append(_mk_field("regular_hours", hours))
    if rate is not None:
        fields.append(_mk_field("hourly_rate", rate))
    if gross is not None:
        fields.append(_mk_field("gross_pay", gross))
    return DocumentExtractionResult(
        document_id=doc_id, document_type=dtype, fields=fields, security_flags=[]
    )


class GrossTotalConflictTests(unittest.TestCase):
    def test_hh002_conflict(self):
        doc = _pay_stub("HH-002-D02", hours=40, rate=24.0, gross=1395.0)
        conflicts = detect_gross_total(doc)
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict.code, CONFLICT_PAY_STUB_TOTAL)
        self.assertEqual(conflict.severity, ConflictSeverity.BLOCKING_FOR_CONFIRMATION)
        self.assertEqual(conflict.document_ids, ["HH-002-D02"])
        self.assertEqual(conflict.observed_values["expected_gross"], 960.0)
        self.assertEqual(conflict.observed_values["gross_pay"], 1395.0)
        self.assertEqual(len(conflict.source_refs), 3)
        self.assertEqual(conflict.conflict_id, "HH-002-D02:PAY_STUB_TOTAL_CONFLICT")

    def test_hh001_no_conflict(self):
        doc = _pay_stub("HH-001-D03", hours=76, rate=28.5, gross=2166.0)
        self.assertEqual(detect_gross_total(doc), [])

    def test_correct_hh002_stub_no_conflict(self):
        doc = _pay_stub("HH-002-D03", hours=40, rate=24.0, gross=960.0)
        self.assertEqual(detect_gross_total(doc), [])

    def test_missing_gross_no_conflict(self):
        doc = _pay_stub("X", hours=40, rate=24.0, gross=None)
        self.assertEqual(detect_gross_total(doc), [])

    def test_missing_all_numeric_no_conflict(self):
        doc = _pay_stub("X")
        self.assertEqual(detect_gross_total(doc), [])

    def test_non_pay_stub_ignored(self):
        doc = _pay_stub("HH-001-D01", hours=40, rate=24.0, gross=1395.0,
                        dtype=DocumentType.APPLICATION_SUMMARY)
        self.assertEqual(detect_gross_total(doc), [])

    def test_non_numeric_normalized_value_no_conflict(self):
        doc = _pay_stub("X", hours="forty", rate=24.0, gross=1395.0)
        self.assertEqual(detect_gross_total(doc), [])

    def test_tolerance_edge_within(self):
        doc = _pay_stub("X", hours=40, rate=24.0, gross=960.005)
        self.assertEqual(detect_gross_total(doc), [])

    def test_tolerance_edge_outside(self):
        doc = _pay_stub("X", hours=40, rate=24.0, gross=960.02)
        self.assertEqual(len(detect_gross_total(doc)), 1)

    def test_message_is_non_decisional(self):
        doc = _pay_stub("X", hours=40, rate=24.0, gross=1395.0)
        message = detect_gross_total(doc)[0].message.lower()
        for token in _ELIGIBILITY_TOKENS:
            self.assertNotIn(token, message)

    def test_never_raises_on_odd_input(self):
        # Non-numeric / partial / empty inputs must not raise.
        for doc in (
            _pay_stub("X", hours="forty", rate="n/a", gross="1,395"),
            _pay_stub("X", hours=40),
            _pay_stub("X"),
            DocumentExtractionResult(
                document_id="X", document_type=DocumentType.PAY_STUB,
                fields=[], security_flags=[],
            ),
        ):
            self.assertIsInstance(detect_gross_total(doc), list)


if __name__ == "__main__":
    unittest.main()
