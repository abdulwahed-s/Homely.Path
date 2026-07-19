"""A5: deterministic per-field confidence estimation.

Pure. Combines simple extraction signals into a score in ``[0, 1]`` and a
:class:`ConfidenceLevel` tier. Deliberately minimal — this is estimation, not
statistical calibration (calibration is architecture-prepared but deferred).

Rules (thresholds/caps live in ``config``):
- Start from the classifier confidence (clamped to ``[0, 1]``).
- OCR-derived values are scaled down relative to native text.
- A value with no valid source box has no provenance -> forced LOW.
- A value that failed to normalize is unreliable -> forced LOW.
- A value adjacent to detected injection text can never be rated HIGH.
"""

import math

from backend.ai.contracts.extraction_contract import ConfidenceLevel
from backend.ai.document_evidence.config import (
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_INJECTION_MAX,
    CONFIDENCE_MEDIUM_THRESHOLD,
    CONFIDENCE_NO_BOX_MAX,
    CONFIDENCE_NO_PARSE_MAX,
    CONFIDENCE_OCR_FACTOR,
)
from backend.ai.document_evidence.schemas.internal import ConfidenceSignals

__all__ = ["score_field", "to_level", "estimate"]


def _clamp01(value) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(result):
        return 0.0
    if result < 0.0:
        return 0.0
    if result > 1.0:
        return 1.0
    return result


def score_field(signals: ConfidenceSignals) -> float:
    """Return a deterministic confidence score in ``[0, 1]`` (2 decimals)."""
    score = _clamp01(signals.classifier_confidence)

    if signals.used_ocr:
        score *= CONFIDENCE_OCR_FACTOR
    if signals.injection_near:
        score = min(score, CONFIDENCE_INJECTION_MAX)
    if not signals.box_valid:
        score = min(score, CONFIDENCE_NO_BOX_MAX)
    if not signals.parse_ok:
        score = min(score, CONFIDENCE_NO_PARSE_MAX)

    return round(_clamp01(score), 2)


def to_level(score: float) -> ConfidenceLevel:
    """Map a numeric score to a confidence tier (monotonic)."""
    if score >= CONFIDENCE_HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    if score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def estimate(signals: ConfidenceSignals):
    """Return ``(score, level)`` for the given signals."""
    score = score_field(signals)
    return score, to_level(score)
