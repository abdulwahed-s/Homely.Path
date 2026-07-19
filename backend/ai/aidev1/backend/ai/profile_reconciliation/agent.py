"""Profile Reconciliation Agent: evidence -> structured conflicts.

Consumes the extracted evidence for a household and runs every conflict
detector (per-document gross-total + cross-document). It reports conflicts and
emits activity events; it never decides which document is correct.
"""

from __future__ import annotations

from typing import List, Optional

from backend.ai.contracts.extraction_contract import ActivityEvent, ActivityStatus, DocumentExtractionResult
from backend.ai.document_evidence.activity import AGENT_RECONCILIATION, Clock, SystemClock, make_event
from backend.ai.profile_reconciliation.conflict_types import StructuredConflict
from backend.ai.profile_reconciliation.cross_document import detect_cross_document
from backend.ai.profile_reconciliation.gross_total import detect_gross_total

__all__ = ["ReconciliationResult", "ReconciliationAgent"]


class ReconciliationResult:
    def __init__(self, conflicts: List[StructuredConflict], events: List[ActivityEvent]):
        self.conflicts = conflicts
        self.activity_events = events


class ReconciliationAgent:
    def __init__(self, clock: Optional[Clock] = None):
        self._clock = clock or SystemClock()

    def reconcile(self, documents: List[DocumentExtractionResult]) -> ReconciliationResult:
        conflicts: List[StructuredConflict] = []
        for document in documents:
            conflicts += detect_gross_total(document)
        conflicts += detect_cross_document(documents)

        event = make_event(
            AGENT_RECONCILIATION,
            "reconcile_documents",
            ActivityStatus.ACTION_REQUIRED if conflicts else ActivityStatus.PASS,
            {
                "document_count": len(documents),
                "conflict_count": len(conflicts),
                "conflict_codes": [c.code for c in conflicts],
            },
            clock=self._clock,
        )
        return ReconciliationResult(conflicts, [event])
