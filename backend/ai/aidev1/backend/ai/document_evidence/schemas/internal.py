"""Internal DTOs shared across Document Evidence Agent modules.

Introduced incrementally by the A-phase steps:
- ``BoxError``        (A3) — a source-box validation failure.
- ``InjectionReport`` (A4) — result of scanning document text for injection.
- ``ConfidenceSignals`` (A5) — inputs to confidence estimation.

All types are plain dataclasses. ``InjectionReport`` references the frozen
``SecurityFlag`` enum via the canonical contract path (Step 0 shim).
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from backend.ai.contracts.extraction_contract import SecurityFlag


@dataclass(frozen=True)
class BoxError:
    """A source-box validation failure (A3).

    Immutable so it can be safely returned and compared. ``box`` stores the
    offending input as-provided (it may be malformed, e.g. wrong length), which
    is useful for diagnostics and downstream ``requires_manual_entry`` handling.
    """

    reason: str
    page: Any
    box: Any
    field_name: Optional[str] = None


@dataclass
class InjectionReport:
    """Result of scanning document text for embedded injection (A4)."""

    flagged: bool = False
    matched_spans: List[str] = field(default_factory=list)
    flags: List[SecurityFlag] = field(default_factory=list)


@dataclass
class ConfidenceSignals:
    """Inputs to confidence estimation (A5).

    Defaults are deliberately conservative: with no positive evidence a field
    scores LOW (missing box / failed parse dominate).
    """

    classifier_confidence: float = 0.0
    used_ocr: bool = False
    box_valid: bool = False
    parse_ok: bool = False
    injection_near: bool = False
