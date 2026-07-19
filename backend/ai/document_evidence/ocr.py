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

__all__ = [
    "OCRWord",
    "OCREngine",
    "RapidOCREngine",
    "LazyOCREngine",
    "build_ocr_engine",
]


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
    """OCR backed by ``rapidocr-onnxruntime`` (line-level boxes).

    Configured to be memory-frugal so it can run on small (512 MB) deploy
    instances: single-threaded onnxruntime sessions (smaller thread arenas) and
    a capped detection side length (smaller inference tensors). These knobs
    reduce peak RSS at a small latency cost.
    """

    def __init__(self):
        import os

        # Keep native thread pools tiny before onnxruntime spins them up.
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("ORT_DISABLE_ALL_OPTIMIZATION", "0")

        from rapidocr_onnxruntime import RapidOCR

        frugal = {
            "intra_op_num_threads": 1,
            "inter_op_num_threads": 1,
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        }
        try:
            self._engine = RapidOCR(**frugal)
        except TypeError:
            # Older/newer RapidOCR signatures may not accept these kwargs.
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


class LazyOCREngine:
    """Build RapidOCR on first ``recognize`` call only.

    Loading ONNX models is memory-heavy (~hundreds of MB). On small Render
    instances that can OOM-kill the worker on the *first* extract even when the
    PDF is text-based and OCR is never needed. This proxy keeps OCR optional
    and defers the cost until a rasterized page actually requires it.
    """

    def __init__(self):
        self._inner: Optional[OCREngine] = None
        self._failed = False

    def recognize(self, png_bytes: bytes) -> List[OCRWord]:
        if self._failed:
            return []
        if self._inner is None:
            try:
                self._inner = RapidOCREngine()
            except Exception:  # noqa: BLE001 - OCR is optional
                self._failed = True
                return []
        return self._inner.recognize(png_bytes)


def build_ocr_engine(*, lazy: bool = True) -> Optional[OCREngine]:
    """Return an OCR engine, or ``None`` if OCR is disabled/unavailable.

    Set ``REALDOOR_DISABLE_OCR=1`` to turn OCR off entirely: rasterized pages
    then degrade to manual entry instead of loading onnxruntime — a safety
    valve for instances too small to hold the OCR models in RAM.

    Default ``lazy=True`` avoids loading ONNX until the first rasterized page
    needs it. Pass ``lazy=False`` for tests that want it warmed immediately.
    """
    import os

    if os.environ.get("REALDOOR_DISABLE_OCR", "").strip().lower() in {"1", "true", "yes"}:
        return None
    if lazy:
        return LazyOCREngine()
    try:
        return RapidOCREngine()
    except Exception:  # noqa: BLE001 - OCR is optional; degrade gracefully
        return None
