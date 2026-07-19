"""A6: local structured-conflict model for the Reconciliation Agent.

These types are AI Developer 1-local until the Integration Owner freezes a
shared ``reconciliation_contract`` (deferred E4). ``StructuredConflict`` reports
evidence only — it never names a "correct" value.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from contracts.extraction_contract import SourceBox

__all__ = [
    "ConflictSeverity",
    "StructuredConflict",
    "CONFLICT_PAY_STUB_TOTAL",
    "CONFLICT_PAY_FREQUENCY",
    "CONFLICT_OVERLAPPING_PERIODS",
    "CONFLICT_PERSON_NAME",
]

# Stable conflict codes consumed by downstream readiness (checklist reasons).
CONFLICT_PAY_STUB_TOTAL = "PAY_STUB_TOTAL_CONFLICT"
CONFLICT_PAY_FREQUENCY = "PAY_FREQUENCY_CONFLICT"
CONFLICT_OVERLAPPING_PERIODS = "OVERLAPPING_PAY_PERIODS"
CONFLICT_PERSON_NAME = "PERSON_NAME_CONFLICT"


class ConflictSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING_FOR_CONFIRMATION = "blocking_for_confirmation"


@dataclass
class StructuredConflict:
    """A reported conflict requiring human confirmation.

    ``observed_values`` records what was seen (evidence), not a resolution.
    """

    conflict_id: str
    code: str
    severity: ConflictSeverity
    message: str
    document_ids: List[str] = field(default_factory=list)
    field_names: List[str] = field(default_factory=list)
    observed_values: Dict[str, Any] = field(default_factory=dict)
    source_refs: List[SourceBox] = field(default_factory=list)
