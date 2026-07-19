"""Confidence calibration (FR1.13): map raw scores to empirical accuracy.

Uses histogram binning: the ``[0, 1]`` score range is split into fixed buckets;
each bucket learns the observed fraction of *correct* extractions (value + box)
from the organizer gold data. At runtime the extractor maps a raw score to the
accuracy of its bucket, so a reported confidence reflects measured reliability.

The fitted model is persisted to ``calibration_data.json`` next to this module.
When no model is present, calibration is the identity (raw score passthrough).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

__all__ = [
    "CalibrationModel",
    "fit",
    "identity",
    "load_default",
    "get_active",
    "set_active",
    "DATA_PATH",
]

DATA_PATH = Path(__file__).resolve().parent / "calibration_data.json"
_DEFAULT_BINS = 10


@dataclass
class CalibrationModel:
    n_bins: int = _DEFAULT_BINS
    # Per-bucket learned accuracy; None means "no data, pass through".
    accuracy: List[Optional[float]] = field(default_factory=list)
    counts: List[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.accuracy:
            self.accuracy = [None] * self.n_bins
            self.counts = [0] * self.n_bins

    def has_learned_data(self) -> bool:
        """True if at least one bucket has a fitted accuracy (i.e. not identity)."""
        return any(a is not None for a in self.accuracy)

    def _bucket(self, score: float) -> int:
        clamped = min(max(score, 0.0), 1.0)
        return min(int(clamped * self.n_bins), self.n_bins - 1)

    def apply(self, raw_score: float) -> float:
        """Return the calibrated score for ``raw_score``.

        Falls back to the raw score for buckets with no observations.
        """
        bucket = self._bucket(raw_score)
        learned = self.accuracy[bucket]
        if learned is None:
            return round(min(max(raw_score, 0.0), 1.0), 2)
        return round(learned, 2)

    def to_dict(self) -> dict:
        return {"n_bins": self.n_bins, "accuracy": self.accuracy, "counts": self.counts}

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationModel":
        model = cls(n_bins=int(data.get("n_bins", _DEFAULT_BINS)))
        model.accuracy = list(data.get("accuracy", model.accuracy))
        model.counts = list(data.get("counts", model.counts))
        return model

    def save(self, path: Optional[Path] = None) -> None:
        (path or DATA_PATH).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def identity(n_bins: int = _DEFAULT_BINS) -> CalibrationModel:
    """A passthrough model (no learned data)."""
    return CalibrationModel(n_bins=n_bins)


def fit(samples: Sequence[Tuple[float, bool]], n_bins: int = _DEFAULT_BINS) -> CalibrationModel:
    """Fit a calibration model from ``(score, correct)`` samples."""
    model = CalibrationModel(n_bins=n_bins)
    correct_counts = [0] * n_bins
    for score, correct in samples:
        bucket = model._bucket(float(score))
        model.counts[bucket] += 1
        if correct:
            correct_counts[bucket] += 1
    for i in range(n_bins):
        if model.counts[i] > 0:
            model.accuracy[i] = round(correct_counts[i] / model.counts[i], 3)
    return model


def load_default() -> CalibrationModel:
    """Load the persisted model, or an identity model if none exists."""
    if DATA_PATH.is_file():
        try:
            return CalibrationModel.from_dict(json.loads(DATA_PATH.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            return identity()
    return identity()


# Process-wide active model, lazily loaded. The extractor consults this.
_active: Optional[CalibrationModel] = None


def get_active() -> CalibrationModel:
    global _active
    if _active is None:
        _active = load_default()
    return _active


def set_active(model: CalibrationModel) -> None:
    global _active
    _active = model
