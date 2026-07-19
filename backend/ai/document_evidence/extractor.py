"""B2: allowlisted extraction engine.

Calls the injected :class:`VisionLLM` to read only the allowlisted fields for a
document type, then assembles frozen-contract :class:`ExtractedField` objects by
combining:

- ``normalize`` (A2) for typed/display values,
- ``pdf_loader.locate_value_box`` + ``boxes`` (A3) for source boxes,
- ``confidence`` (A5) for per-field score/level.

Off-allowlist keys returned by the model are ignored. Fields the model could
not read (null/empty) are skipped.
"""

from __future__ import annotations

from typing import Any, Dict, List

from contracts.extraction_contract import (
    ConfidenceLevel,
    ConfirmationStatus,
    ExtractedField,
    SourceBox,
)
from backend.ai.document_evidence import allowlist, calibration, prompts
from backend.ai.document_evidence.boxes import build_source_description, make_source_box
from backend.ai.document_evidence.confidence import score_field, to_level
from backend.ai.document_evidence.llm import LLMError
from backend.ai.document_evidence.llm_openai import build_multimodal_messages
from backend.ai.document_evidence.normalize import normalize_field
from backend.ai.document_evidence.pdf_loader import LoadedDocument, locate_value_box
from backend.ai.document_evidence.schemas.internal import ConfidenceSignals

__all__ = ["extract_raw", "build_fields", "extract_document"]


def _type_value(document_type) -> str:
    return getattr(document_type, "value", document_type)


def extract_raw(
    document: LoadedDocument,
    document_type,
    llm,
) -> Dict[str, Any]:
    """Ask the model for the allowlisted fields. Returns a raw name->value dict.

    Never raises: on model failure returns an empty dict (all fields become
    manual entry downstream).
    """
    fields = allowlist.fields_for(document_type)
    if not fields:
        return {}

    first = document.pages[0] if document.pages else None
    image_present = bool(first and first.is_rasterized)
    text = document.full_text

    text_messages = prompts.build_extract_prompt(
        _type_value(document_type), fields, text, image_present
    )
    image_uri = first.data_uri() if (first and image_present) else None
    messages = build_multimodal_messages(text_messages, image_uri)
    schema = prompts.OUTPUT_SCHEMA_FOR(_type_value(document_type))

    try:
        result = llm.complete_json(messages, schema)
    except LLMError:
        return {}
    if not isinstance(result, dict):
        return {}
    return result


def _unwrap(value: Any) -> Any:
    """Accept either a scalar or a ``{"value": ...}`` object from the model."""
    if isinstance(value, dict):
        for key in ("value", "text", "raw"):
            if key in value:
                return value[key]
        return None
    return value


def _extract_model_bbox(raw: Any) -> Any:
    """Return a normalized ``[x0,y0,x1,y1]`` (top-left origin) from a model
    ``{"value":..., "bbox":[...]}`` object, or ``None`` if absent/malformed."""
    if not isinstance(raw, dict):
        return None
    bbox = raw.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None
    try:
        return [float(c) for c in bbox]
    except (TypeError, ValueError):
        return None


def _model_box_to_points(page, bbox_norm) -> Any:
    """Convert a normalized top-left ``[x0,y0,x1,y1]`` box (model-provided) into a
    bottom-left-origin PDF-point box, or ``None`` if degenerate.

    Mirrors ``pdf_loader``'s ``page_height - y`` flip. Coordinates are clamped
    to ``[0,1]`` first so a slightly out-of-range model box is still usable.
    """
    if page is None or bbox_norm is None:
        return None
    try:
        x0, y0, x1, y1 = (min(max(float(v), 0.0), 1.0) for v in bbox_norm)
    except (TypeError, ValueError):
        return None
    width = float(page.width)
    height = float(page.height)
    x_lo, x_hi = min(x0, x1) * width, max(x0, x1) * width
    # image top-left origin -> pdf bottom-left origin (flip Y)
    y_lo = height * (1.0 - max(y0, y1))
    y_hi = height * (1.0 - min(y0, y1))
    if (x_hi - x_lo) <= 0.5 or (y_hi - y_lo) <= 0.5:
        return None  # degenerate / zero-area box
    return (round(x_lo, 2), round(y_lo, 2), round(x_hi, 2), round(y_hi, 2))


def _find_box(document: LoadedDocument, display, normalized):
    """Return ``(page, box, used_ocr)`` for a value, or ``(None, None, ocr)``."""
    for page in document.pages:
        box = locate_value_box(page, display, normalized)
        if box is not None:
            return page, box, page.is_rasterized
    return None, None, document.is_rasterized


def _fallback_source(document: LoadedDocument, field_name: str, document_type: str) -> SourceBox:
    first = document.pages[0] if document.pages else None
    width = first.width if first else 612.0
    height = first.height if first else 792.0
    return SourceBox(
        page=1,
        x1=0.0,
        y1=0.0,
        x2=float(width),
        y2=float(height),
        source_description=(
            build_source_description(field_name, document_type, 1)
            + " (approximate: exact location unavailable)"
        ),
    )


def build_fields(
    document: LoadedDocument,
    document_type,
    raw_values: Dict[str, Any],
    classification_confidence: float,
    injection_flagged: bool,
) -> List[ExtractedField]:
    """Assemble :class:`ExtractedField` objects for the allowlisted fields."""
    type_value = _type_value(document_type)
    fields: List[ExtractedField] = []

    for field_name in allowlist.fields_for(document_type):
        raw_obj = raw_values.get(field_name)
        raw = _unwrap(raw_obj)
        display, normalized = normalize_field(field_name, raw)
        if display is None and normalized is None:
            continue  # model did not read this field

        page, box, used_ocr = _find_box(document, display, normalized)
        box_valid = False
        model_located = False
        source = None
        if box is not None and page is not None:
            source_or_error = make_source_box(
                page.page_number, box, field_name, type_value, (page.width, page.height)
            )
            if isinstance(source_or_error, SourceBox):
                source = source_or_error
                box_valid = True

        if source is None:
            # No text-layer / OCR match: fall back to a box the vision model
            # located itself (no OCR dependency; used for rasterized pages).
            first = document.pages[0] if document.pages else None
            model_box = _model_box_to_points(first, _extract_model_bbox(raw_obj))
            if model_box is not None and first is not None:
                candidate = make_source_box(
                    first.page_number, model_box, field_name, type_value,
                    (first.width, first.height),
                )
                if isinstance(candidate, SourceBox):
                    source = SourceBox(
                        page=candidate.page,
                        x1=candidate.x1,
                        y1=candidate.y1,
                        x2=candidate.x2,
                        y2=candidate.y2,
                        source_description=(
                            candidate.source_description
                            + " (located by vision model; approximate)"
                        ),
                    )
                    model_located = True

        if source is None:
            source = _fallback_source(document, field_name, type_value)

        parse_ok = normalized is not None
        raw_score = score_field(
            ConfidenceSignals(
                classifier_confidence=classification_confidence,
                used_ocr=used_ocr,
                box_valid=box_valid,
                model_located=model_located,
                parse_ok=parse_ok,
                injection_near=injection_flagged,
            )
        )
        # FR1.13: map the raw score through the gold-fitted calibration model.
        # The calibration was fit on text/OCR-located fields, so it is not
        # applied to model-located boxes (their score is already MEDIUM-capped).
        score = raw_score if model_located else calibration.get_active().apply(raw_score)
        level = to_level(score)

        # FR1.6 / FR1.13: low-confidence values are never prefilled (never
        # guessed). We keep the field and its source so the UI can point at
        # where the value should be, but blank the value and force manual entry.
        # medium/high (incl. model-located) are prefilled and require confirm.
        is_low = level == ConfidenceLevel.LOW
        has_provenance = box_valid or model_located
        requires_manual_entry = is_low or (not has_provenance) or (not parse_ok)
        out_value = None if is_low else display
        out_normalized = None if is_low else normalized

        fields.append(
            ExtractedField(
                field_name=field_name,
                value=out_value,
                normalized_value=out_normalized,
                confidence=score,
                confidence_level=level,
                confirmation_status=ConfirmationStatus.AWAITING_CONFIRMATION,
                source=source,
                requires_manual_entry=requires_manual_entry,
            )
        )
    return fields


def extract_document(
    document: LoadedDocument,
    document_type,
    llm,
    classification_confidence: float = 0.9,
    injection_flagged: bool = False,
) -> List[ExtractedField]:
    """Convenience: raw model extraction + field assembly in one call."""
    raw = extract_raw(document, document_type, llm)
    return build_fields(
        document, document_type, raw, classification_confidence, injection_flagged
    )
