"""A4: prompt-injection / adversarial text detection.

Pure, deterministic heuristics (no model calls). Document text is untrusted
input (CH-SAFETY-001): embedded instructions must be detected and flagged, and
never executed or surfaced as a profile field.

Detection is intentionally conservative to avoid false positives on legitimate
document text. It anchors on instruction-style phrasings (ignore/disregard
instructions, reveal the system prompt, mark approved, etc.), which covers the
organizer adversarial fixtures.
"""

import re
from typing import List, Optional

from backend.ai.contracts.extraction_contract import SecurityFlag
from backend.ai.document_evidence.schemas.internal import InjectionReport

__all__ = ["INJECTION_PATTERNS", "scan_text"]

INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+|the\s+|any\s+|your\s+|prior\s+|previous\s+|above\s+)*instructions",
    r"disregard\s+(?:all\s+|the\s+|any\s+|your\s+|prior\s+|previous\s+|above\s+)*instructions",
    r"forget\s+(?:all\s+|the\s+|any\s+|your\s+|prior\s+|previous\s+|above\s+)*instructions",
    r"override\s+(?:all\s+|the\s+|any\s+|your\s+|prior\s+|previous\s+)*instructions",
    r"reveal\s+(?:the\s+|your\s+)?system\s+prompt",
    r"show\s+(?:me\s+)?(?:the\s+|your\s+)?system\s+prompt",
    r"print\s+(?:the\s+|your\s+)?(?:system\s+prompt|instructions)",
    r"mark\s+(?:this\s+)?(?:applicant\s+)?(?:as\s+)?approved",
    r"you\s+are\s+now\s+",
    r"developer\s+mode",
)

_COMPILED = tuple(re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS)


def scan_text(text: Optional[str]) -> InjectionReport:
    """Scan document text for embedded injection instructions.

    Returns an :class:`InjectionReport`. When any pattern matches, ``flagged``
    is ``True``, ``flags`` contains ``PROMPT_INJECTION_DETECTED``, and
    ``matched_spans`` holds the unique matched substrings (order preserved).
    Never raises; ``None`` or empty text yields an unflagged report.
    """
    if not text:
        return InjectionReport()

    # Collapse whitespace so line-broken / OCR'd instructions still match.
    normalized = " ".join(str(text).split())

    matched_spans: List[str] = []
    for pattern in _COMPILED:
        for match in pattern.finditer(normalized):
            span = match.group(0).strip()
            if span and span not in matched_spans:
                matched_spans.append(span)

    if not matched_spans:
        return InjectionReport()

    return InjectionReport(
        flagged=True,
        matched_spans=matched_spans,
        flags=[SecurityFlag.PROMPT_INJECTION_DETECTED],
    )
