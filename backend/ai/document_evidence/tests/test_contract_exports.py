"""Step 0 tests: the canonical extraction contract is imported from root.

Verifies that ``contracts.extraction_contract`` exposes every contract symbol
and that the root package is the source of truth.
"""

import sys
import unittest
from pathlib import Path

# Put the repo root on the path so ``contracts`` resolves. Mirrors the
# organizer starter style.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import contracts.extraction_contract as source  # noqa: E402

EXPECTED_NAMES = [
    "ActivityEvent",
    "ActivityStatus",
    "ConfidenceLevel",
    "ConfirmationStatus",
    "DocumentExtractionResult",
    "DocumentType",
    "ExtractedField",
    "ExtractionResponse",
    "SecurityFlag",
    "SourceBox",
]


class ContractExportTests(unittest.TestCase):
    def test_root_is_canonical_contract_package(self):
        self.assertTrue((ROOT / "contracts" / "extraction_contract.py").is_file())

    def test_all_expected_names_present(self):
        for name in EXPECTED_NAMES:
            self.assertTrue(hasattr(source, name), f"contract missing {name}")

    def test_names_are_identical_objects(self):
        from contracts.extraction_contract import ExtractionResponse

        self.assertIs(ExtractionResponse, source.ExtractionResponse)

    def test_all_exports_declared_exactly(self):
        self.assertEqual(sorted(source.__all__), sorted(EXPECTED_NAMES))

    def test_canonical_path_import_works(self):
        from contracts.extraction_contract import ExtractionResponse

        self.assertIs(ExtractionResponse, source.ExtractionResponse)


if __name__ == "__main__":
    unittest.main()