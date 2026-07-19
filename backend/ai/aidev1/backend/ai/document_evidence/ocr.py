"""OCR engine for rasterized pages (RapidOCR / ONNX; no system Tesseract).

Provides line-level text boxes in *pixel* coordinates (top-left origin). The
PDF loader converts these to PDF points and uses them to locate value boxes on
image-only pages. The engine is injectable so the rest of the code never hard-
depends on the OCR provider.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Protocol, runtime_checkable

__all__ = ["OCRWord", "OCREngine", "RapidOCREngine", "build_ocr_engine"]


@dataclass(frozen=True)
class OCRWord:
    """A recognized text segment in pixel coordinates (top-left origin)."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@runtime_checkable
class OCREngine(Protocol):
    def recognize(self, png_bytes: bytes) -> List[OCRWord]:  # pragma: no cover
        ...


class RapidOCREngine:
    """OCR backed by ``rapidocr-onnxruntime`` (line-level boxes)."""

    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    def recognize(self, png_bytes: bytes) -> List[OCRWord]:
        import numpy as np
        from PIL import Image

        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        array = np.array(image)
        result, _ = self._engine(array)
        words: List[OCRWord] = []
        if not result:
            return words
        for box, text, _score in result:
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            words.append(
                OCRWord(str(text), float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys)))
            )
        return words


def build_ocr_engine() -> Optional[OCREngine]:
    """Return a RapidOCR engine, or ``None`` if OCR is unavailable."""
    try:
        return RapidOCREngine()
    except Exception:  # noqa: BLE001 - OCR is optional; degrade gracefully
        return None
