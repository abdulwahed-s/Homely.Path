"""A3: source-box validation and accessible source descriptions.

Pure. Enforces the organizer box convention
(``pdf_points_bottom_left_origin``, coordinates inside the page) and builds a
human-readable, accessible ``source_description`` for a :class:`SourceBox`.

The validation mirrors the organizer starter check
(``starter/src/load_documents.validate_boxes``):
``0 <= x1 < x2 <= width`` and ``0 <= y1 < y2 <= height``.
"""

import math
from typing import Optional, Sequence, Tuple, Union

from backend.ai.contracts.extraction_contract import SourceBox
from backend.ai.document_evidence.schemas.internal import BoxError

__all__ = [
    "PAGE_WIDTH",
    "PAGE_HEIGHT",
    "validate_box",
    "build_source_description",
    "make_source_box",
]

PAGE_WIDTH: float = 612.0
PAGE_HEIGHT: float = 792.0

Box = Sequence[float]
PageSize = Sequence[float]


def _is_finite_number(value) -> bool:
    # Exclude bool explicitly (bool is a subclass of int).
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _label(value) -> str:
    """Human label from an identifier or enum-like value."""
    raw = getattr(value, "value", value)
    return str(raw).replace("_", " ").strip()


def validate_box(
    page: int,
    box: Box,
    page_size: PageSize = (PAGE_WIDTH, PAGE_HEIGHT),
) -> Optional[BoxError]:
    """Validate a page-level PDF-point box.

    Returns ``None`` when valid, otherwise a :class:`BoxError` describing the
    first failure. Never raises.
    """
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        return BoxError("page must be a positive integer", page, box)

    try:
        x1, y1, x2, y2 = box
    except (TypeError, ValueError):
        return BoxError("box must have exactly four values", page, box)

    try:
        width = float(page_size[0])
        height = float(page_size[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return BoxError("page_size must be a (width, height) pair", page, box)

    if not (width > 0 and height > 0):
        return BoxError("page_size dimensions must be positive", page, box)

    for coord in (x1, y1, x2, y2):
        if not _is_finite_number(coord):
            return BoxError("box coordinates must be finite numbers", page, box)

    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)

    if not (0 <= x1 < x2 <= width):
        return BoxError(
            "x-range invalid: require 0 <= x1 < x2 <= width", page, (x1, y1, x2, y2)
        )
    if not (0 <= y1 < y2 <= height):
        return BoxError(
            "y-range invalid: require 0 <= y1 < y2 <= height", page, (x1, y1, x2, y2)
        )
    return None


def build_source_description(field_name: str, document_type: str, page: int) -> str:
    """Return an accessible, human-readable description of a field's location."""
    field_label = _label(field_name) or "value"
    doc_label = _label(document_type) or "document"
    return f"'{field_label}' on page {page} of the {doc_label} document"


def make_source_box(
    page: int,
    box: Box,
    field_name: str,
    document_type: str,
    page_size: PageSize = (PAGE_WIDTH, PAGE_HEIGHT),
) -> Union[SourceBox, BoxError]:
    """Build a validated :class:`SourceBox`, or a :class:`BoxError` if invalid.

    On failure the returned error is annotated with ``field_name`` so callers
    can mark the field ``requires_manual_entry`` downstream.
    """
    error = validate_box(page, box, page_size)
    if error is not None:
        return BoxError(error.reason, error.page, error.box, field_name)

    x1, y1, x2, y2 = box
    return SourceBox(
        page=page,
        x1=float(x1),
        y1=float(y1),
        x2=float(x2),
        y2=float(y2),
        source_description=build_source_description(field_name, document_type, page),
    )
