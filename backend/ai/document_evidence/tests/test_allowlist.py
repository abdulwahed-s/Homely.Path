"""Step A1 tests: allowlist parity with organizer gold and edge cases.

The allowlist is the scored extraction surface. These tests bind it to the
organizer gold file so drift is caught immediately, and they exercise the
public helpers' edge cases (unknown types, ``None``, mutation-safety, security
fields, enum keys).
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.document_evidence.allowlist import (  # noqa: E402
    ALLOWLIST,
    SECURITY_ONLY_FIELDS,
    fields_for,
    is_allowed,
)

GOLD_PATH = (
    ROOT
    / "organizer_pack"
    / "synthetic_documents"
    / "gold"
    / "document_gold.jsonl"
)

EXPECTED_TYPES = {
    "application_summary",
    "pay_stub",
    "employment_letter",
    "benefit_letter",
    "gig_statement",
}


def _gold_fields_by_type():
    """Map each gold document_type -> set of field names present in gold."""
    mapping: dict[str, set[str]] = {}
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            dtype = record["document_type"]
            names = mapping.setdefault(dtype, set())
            for field in record["fields"]:
                names.add(field["field"])
    return mapping


class AllowlistGoldParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gold = _gold_fields_by_type()

    def test_gold_file_exists(self):
        self.assertTrue(GOLD_PATH.is_file(), f"missing gold: {GOLD_PATH}")

    def test_allowlist_covers_exactly_the_five_types(self):
        self.assertEqual(set(ALLOWLIST.keys()), EXPECTED_TYPES)

    def test_gold_contains_exactly_the_five_types(self):
        self.assertEqual(set(self.gold.keys()), EXPECTED_TYPES)

    def test_allowlist_matches_gold_minus_security_fields(self):
        for dtype, gold_fields in self.gold.items():
            scored_gold = gold_fields - SECURITY_ONLY_FIELDS
            self.assertEqual(
                set(ALLOWLIST[dtype]),
                scored_gold,
                f"allowlist/gold mismatch for {dtype}",
            )

    def test_no_security_field_leaks_into_allowlist(self):
        for dtype, fields in ALLOWLIST.items():
            for security_field in SECURITY_ONLY_FIELDS:
                self.assertNotIn(security_field, fields, dtype)

    def test_no_duplicate_fields_within_a_type(self):
        for dtype, fields in ALLOWLIST.items():
            self.assertEqual(len(fields), len(set(fields)), dtype)


class FieldsForTests(unittest.TestCase):
    def test_returns_canonical_order(self):
        self.assertEqual(
            fields_for("pay_stub"),
            [
                "person_name",
                "pay_date",
                "pay_period_start",
                "pay_period_end",
                "pay_frequency",
                "regular_hours",
                "hourly_rate",
                "gross_pay",
                "net_pay",
            ],
        )

    def test_unknown_type_returns_empty_list(self):
        self.assertEqual(fields_for("not_a_real_type"), [])

    def test_none_returns_empty_list(self):
        self.assertEqual(fields_for(None), [])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(fields_for(""), [])

    def test_returns_a_fresh_copy_each_call(self):
        first = fields_for("benefit_letter")
        first.append("tampered")
        second = fields_for("benefit_letter")
        self.assertNotIn("tampered", second)
        self.assertNotIn("tampered", ALLOWLIST["benefit_letter"])

    def test_accepts_str_subclass_key(self):
        class StrLike(str):
            pass

        self.assertEqual(fields_for(StrLike("gig_statement")), ALLOWLIST["gig_statement"])

    def test_accepts_document_type_enum_when_available(self):
        try:
            from contracts.extraction_contract import DocumentType
        except Exception:  # pragma: no cover - pydantic/contract not installed
            self.skipTest("contract/pydantic unavailable in this environment")
        self.assertEqual(fields_for(DocumentType.PAY_STUB), ALLOWLIST["pay_stub"])
        self.assertEqual(fields_for(DocumentType.APPLICATION_SUMMARY), ALLOWLIST["application_summary"])
        self.assertEqual(fields_for(DocumentType.UNKNOWN), [])


class IsAllowedTests(unittest.TestCase):
    def test_every_allowlisted_field_is_allowed(self):
        for dtype, fields in ALLOWLIST.items():
            for field_name in fields:
                self.assertTrue(is_allowed(dtype, field_name), f"{dtype}.{field_name}")

    def test_security_field_is_never_allowed(self):
        for dtype in ALLOWLIST:
            self.assertFalse(is_allowed(dtype, "untrusted_instruction_text"), dtype)

    def test_off_allowlist_field_is_rejected(self):
        self.assertFalse(is_allowed("pay_stub", "employer_name"))
        self.assertFalse(is_allowed("pay_stub", "ytd_gross"))
        self.assertFalse(is_allowed("application_summary", "gross_pay"))

    def test_unknown_type_rejects_any_field(self):
        self.assertFalse(is_allowed("not_a_real_type", "person_name"))

    def test_none_inputs_are_rejected(self):
        self.assertFalse(is_allowed(None, "person_name"))
        self.assertFalse(is_allowed("pay_stub", None))

    def test_cross_type_field_isolation(self):
        # A field valid for one type is not implicitly valid for another.
        self.assertTrue(is_allowed("benefit_letter", "monthly_benefit"))
        self.assertFalse(is_allowed("pay_stub", "monthly_benefit"))


class SecurityOnlyFieldsTests(unittest.TestCase):
    def test_is_frozenset(self):
        self.assertIsInstance(SECURITY_ONLY_FIELDS, frozenset)

    def test_contains_untrusted_instruction_text(self):
        self.assertIn("untrusted_instruction_text", SECURITY_ONLY_FIELDS)


if __name__ == "__main__":
    unittest.main()
