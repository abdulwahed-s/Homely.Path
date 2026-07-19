"""Gold-parity evaluation for extraction (values + source boxes).

Compares a :class:`DocumentExtractionResult` against the organizer gold record:
- value correctness (type-aware, tolerant for numbers),
- source-box accuracy via intersection-over-union (IoU) against the gold bbox.

Produces per-field records and dataset summaries, and the ``(confidence,
correct)`` samples used to fit confidence calibration (FR1.13).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from contracts.extraction_contract import DocumentExtractionResult
from backend.ai.document_evidence.allowlist import SECURITY_ONLY_FIELDS
from backend.ai.document_evidence.normalize import normalize_field

__all__ = [
    "FieldEval",
    "iou",
    "value_matches",
    "evaluate_document",
    "evaluate_dataset",
    "summarize",
    "calibration_samples",
]

# A source box counts as correct when it overlaps the gold box by at least this.
IOU_THRESHOLD = 0.5
Box = Tuple[float, float, float, float]


@dataclass(frozen=True)
class FieldEval:
    document_id: str
    field_name: str
    present: bool
    value_correct: bool
    iou: float
    box_correct: bool
    confidence: float
    confidence_level: str

    @property
    def field_correct(self) -> bool:
        return self.value_correct and self.box_correct


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def value_matches(field_name: str, extracted_norm, gold_value) -> bool:
    _, gold_norm = normalize_field(field_name, gold_value)
    if gold_norm is None:
        return extracted_norm is None
    if isinstance(gold_norm, (int, float)) and isinstance(extracted_norm, (int, float)):
        return abs(float(gold_norm) - float(extracted_norm)) <= 0.01
    return str(extracted_norm).strip().lower() == str(gold_norm).strip().lower()


def _gold_fields(gold_record: Dict) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for field in gold_record.get("fields", []):
        name = field.get("field")
        if name and name not in SECURITY_ONLY_FIELDS:
            out[name] = field
    return out


def evaluate_document(result: DocumentExtractionResult, gold_record: Dict) -> List[FieldEval]:
    extracted = {f.field_name: f for f in result.fields}
    evals: List[FieldEval] = []

    for name, gold in _gold_fields(gold_record).items():
        field = extracted.get(name)
        if field is None:
            evals.append(
                FieldEval(result.document_id, name, False, False, 0.0, False, 0.0, "low")
            )
            continue

        value_correct = value_matches(name, field.normalized_value, gold.get("value"))
        gold_box = gold.get("bbox")
        got_box = (field.source.x1, field.source.y1, field.source.x2, field.source.y2)
        overlap = iou(got_box, tuple(gold_box)) if gold_box else 0.0
        evals.append(
            FieldEval(
                document_id=result.document_id,
                field_name=name,
                present=True,
                value_correct=value_correct,
                iou=round(overlap, 3),
                box_correct=overlap >= IOU_THRESHOLD,
                confidence=field.confidence,
                confidence_level=field.confidence_level.value,
            )
        )
    return evals


def evaluate_dataset(
    results: Sequence[DocumentExtractionResult], gold_index: Dict[str, Dict]
) -> List[FieldEval]:
    evals: List[FieldEval] = []
    for result in results:
        gold = gold_index.get(result.document_id)
        if gold is not None:
            evals.extend(evaluate_document(result, gold))
    return evals


def calibration_samples(evals: Sequence[FieldEval]) -> List[Tuple[float, bool]]:
    """``(confidence, field_correct)`` pairs for present fields only."""
    return [(e.confidence, e.field_correct) for e in evals if e.present]


def summarize(evals: Sequence[FieldEval]) -> Dict:
    total = len(evals)
    present = [e for e in evals if e.present]
    value_ok = sum(1 for e in evals if e.value_correct)
    box_ok = sum(1 for e in evals if e.box_correct)
    mean_iou = round(sum(e.iou for e in present) / len(present), 3) if present else 0.0

    tiers: Dict[str, Dict[str, float]] = {}
    for tier in ("high", "medium", "low"):
        bucket = [e for e in present if e.confidence_level == tier]
        correct = sum(1 for e in bucket if e.field_correct)
        tiers[tier] = {
            "count": len(bucket),
            "accuracy": round(correct / len(bucket), 3) if bucket else 0.0,
        }

    return {
        "fields_expected": total,
        "fields_present": len(present),
        "value_accuracy": round(value_ok / total, 3) if total else 0.0,
        "box_accuracy": round(box_ok / total, 3) if total else 0.0,
        "mean_iou": mean_iou,
        "reliability_by_tier": tiers,
    }
