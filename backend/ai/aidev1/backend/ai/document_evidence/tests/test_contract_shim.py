"""Step 0 tests: the contract path shim re-exports the frozen contract.

Verifies that ``backend.ai.contracts.extraction_contract`` exposes every
contract symbol and that each is the *same object* as the frozen source at
``contracts.extraction_contract`` (i.e. a true re-export, not a copy).
"""

import sys
import unittest
from pathlib import Path

# Put the aidev1 root on the path so both ``contracts`` (frozen source) and
# ``backend.ai.contracts`` (shim) resolve. Mirrors the organizer starter style.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import contracts.extraction_contract as source  # noqa: E402
from backend.ai.contracts import extraction_contract as shim  # noqa: E402

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


class ContractShimTests(unittest.TestCase):
    def test_root_is_aidev1(self):
        # Guards the parents[4] index against accidental folder-depth changes.
        self.assertTrue((ROOT / "contracts" / "extraction_contract.py").is_file())

    def test_all_expected_names_present(self):
        for name in EXPECTED_NAMES:
            self.assertTrue(hasattr(shim, name), f"shim missing {name}")

    def test_names_are_identical_objects(self):
        for name in EXPECTED_NAMES:
            self.assertIs(
                getattr(shim, name),
                getattr(source, name),
                f"{name} is not the same object as the frozen source",
            )

    def test_all_exports_declared_exactly(self):
        self.assertEqual(sorted(shim.__all__), sorted(EXPECTED_NAMES))

    def test_canonical_path_import_works(self):
        from backend.ai.contracts.extraction_contract import ExtractionResponse

        self.assertIs(ExtractionResponse, source.ExtractionResponse)

    def test_shim_adds_no_extra_public_symbols(self):
        public = {n for n in dir(shim) if not n.startswith("_")}
        # Every public name must either be an expected contract symbol or the
        # ``annotations`` future import artifact is absent; nothing else leaks.
        self.assertTrue(public.issuperset(EXPECTED_NAMES))
        unexpected = public - set(EXPECTED_NAMES)
        self.assertEqual(unexpected, set(), f"unexpected exports: {unexpected}")


if __name__ == "__main__":
    unittest.main()
