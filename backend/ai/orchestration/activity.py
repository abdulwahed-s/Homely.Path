from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ActivityStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    WAITING = "WAITING"
    FAILED = "FAILED"


class ActivityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    component: str
    action: str
    status: ActivityStatus
    message: str


def make_activity_event(
    component: str,
    action: str,
    status: ActivityStatus,
    message: str,
) -> ActivityEvent:
    """Do not place names, addresses, income values or raw document text here."""
    return ActivityEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        component=component,
        action=action,
        status=status,
        message=message,
    )
