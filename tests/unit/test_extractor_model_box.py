"""Vision-model-located bounding boxes (no-OCR fallback for rasterized pages)."""

from __future__ import annotations

from backend.ai.document_evidence.extractor import (
    _extract_model_bbox,
    _model_box_to_points,
    build_fields,
)
from backend.ai.document_evidence.pdf_loader import LoadedDocument, LoadedPage
from contracts.extraction_contract import ConfidenceLevel, DocumentType


def _rasterized_page() -> LoadedPage:
    # No words -> text-layer/OCR location fails, forcing the model-box fallback.
    return LoadedPage(
        page_number=1,
        text="",
        width=612.0,
        height=792.0,
        image_png=b"",
        is_rasterized=True,
        words=[],
        ocr_used=False,
    )


def test_model_box_conversion_flips_y_to_bottom_left():
    # Top half of the image (normalized) -> upper half in PDF points.
    assert _model_box_to_points(_rasterized_page(), [0.0, 0.0, 1.0, 0.5]) == (
        0.0,
        396.0,
        612.0,
        792.0,
    )


def test_model_box_rejects_degenerate_and_malformed():
    page = _rasterized_page()
    assert _model_box_to_points(page, [0.5, 0.5, 0.5, 0.5]) is None  # zero area
    assert _model_box_to_points(page, None) is None
    assert _extract_model_bbox({"value": "x", "bbox": [0.1, 0.2, 0.3, 0.4]}) == [0.1, 0.2, 0.3, 0.4]
    assert _extract_model_bbox("scalar") is None
    assert _extract_model_bbox({"value": "x"}) is None
    assert _extract_model_bbox({"value": "x", "bbox": [1, 2, 3]}) is None


def test_build_fields_uses_model_box_when_no_text_layer():
    doc = LoadedDocument(document_id="D", pages=[_rasterized_page()])
    raw = {"gross_pay": {"value": "$1,395.00", "bbox": [0.5, 0.6, 0.7, 0.63]}}

    fields = build_fields(
        doc,
        DocumentType.PAY_STUB,
        raw,
        classification_confidence=0.95,
        injection_flagged=False,
    )
    gross = next(f for f in fields if f.field_name == "gross_pay")

    # Value is retained (not blanked) because the model located a box.
    assert gross.value is not None
    assert gross.normalized_value == 1395.0
    # Model-located boxes are capped at MEDIUM.
    assert gross.confidence_level == ConfidenceLevel.MEDIUM
    assert gross.confidence <= 0.70
    assert "vision model" in gross.source.source_description
    # A real (non full-page fallback) box was produced.
    assert (gross.source.x1, gross.source.y1, gross.source.x2, gross.source.y2) != (0.0, 0.0, 612.0, 792.0)


def test_build_fields_blanks_when_no_box_and_no_model_box():
    doc = LoadedDocument(document_id="D", pages=[_rasterized_page()])
    raw = {"gross_pay": {"value": "$1,395.00", "bbox": None}}  # model gave no box

    fields = build_fields(
        doc,
        DocumentType.PAY_STUB,
        raw,
        classification_confidence=0.95,
        injection_flagged=False,
    )
    gross = next(f for f in fields if f.field_name == "gross_pay")

    assert gross.value is None
    assert gross.requires_manual_entry is True
    assert gross.confidence_level == ConfidenceLevel.LOW
