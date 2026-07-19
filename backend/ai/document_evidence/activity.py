"""A7: structured activity-event emission.

Pure factory with an injectable :class:`Clock` for deterministic timestamps in
tests. Produces frozen-contract :class:`ActivityEvent` objects for the UI/agent
timeline. Does not log, persist, or order events — callers sequence them.
"""

from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable

from contracts.extraction_contract import ActivityEvent, ActivityStatus

__all__ = [
    "Clock",
    "SystemClock",
    "make_event",
    "AGENT_DOCUMENT_EVIDENCE",
    "AGENT_RECONCILIATION",
]

AGENT_DOCUMENT_EVIDENCE = "document_evidence_agent"
AGENT_RECONCILIATION = "reconciliation_agent"


@runtime_checkable
class Clock(Protocol):
    """Time source. Injected so tests can supply deterministic timestamps."""

    def now_iso(self) -> str:  # pragma: no cover - protocol signature
        ...


class SystemClock:
    """Default real clock: current UTC time as an ISO-8601 string."""

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


def make_event(
    agent: str,
    action: str,
    status: ActivityStatus,
    metadata: Optional[dict] = None,
    clock: Optional[Clock] = None,
) -> ActivityEvent:
    """Create an :class:`ActivityEvent`.

    ``metadata`` is copied defensively so the caller's dict cannot be aliased
    into the event. ``clock`` defaults to :class:`SystemClock`.
    """
    active_clock = clock if clock is not None else SystemClock()
    safe_metadata = dict(metadata) if metadata else {}
    return ActivityEvent(
        timestamp=active_clock.now_iso(),
        agent=agent,
        action=action,
        status=status,
        metadata=safe_metadata,
    )
