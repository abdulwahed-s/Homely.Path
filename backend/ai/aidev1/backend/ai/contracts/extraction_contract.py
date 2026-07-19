"""Re-export shim for the frozen extraction contract (Step 0).

Purpose
-------
``organizer_pack/aidev1.txt`` specifies the shared-contract import path as
``aidev1/backend/ai/contracts/`` while the frozen source of truth lives at
``aidev1/contracts/extraction_contract.py``. This module resolves that mismatch
by re-exporting every contract symbol *by reference* from the single source of
truth, so::

    backend.ai.contracts.extraction_contract.X is contracts.extraction_contract.X

Constraints
-----------
- Import-only. This shim MUST NOT add, remove, rename, or redefine any contract
  type. The frozen contract remains the sole authority for their definitions.
- No behaviour, no I/O.
"""

from contracts.extraction_contract import (
    ActivityEvent,
    ActivityStatus,
    ConfidenceLevel,
    ConfirmationStatus,
    DocumentExtractionResult,
    DocumentType,
    ExtractedField,
    ExtractionResponse,
    SecurityFlag,
    SourceBox,
)

__all__ = [
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
