"""PDF loading, rasterization, and value-box location (PyMuPDF).

This is the only I/O boundary for reading uploaded documents. It supports both
text PDFs and rasterized/image PDFs:

- ``load_pdf`` returns per-page text, page size (PDF points), a rendered PNG
  (for the vision model), a per-page ``is_rasterized`` heuristic, and the word
  geometry captured from the text layer.
- ``locate_value_box`` finds where an extracted value appears on a page by
  matching against captured words and converts PyMuPDF's top-left-origin
  rectangle into the organizer's ``pdf_points_bottom_left_origin`` box.

For rasterized pages (no native text layer), an injected OCR engine supplies
line-level word boxes so values can still be located; without OCR,
``locate_value_box`` returns ``None`` and the caller lowers confidence / marks
manual entry.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF

__all__ = [
    "Word",
    "LoadedPage",
    "LoadedDocument",
    "PdfLoadError",
    "load_pdf",
    "locate_value_box",
    "to_data_uri",
]


class PdfLoadError(Exception):
    """Raised when a source cannot be opened/parsed as a PDF.

    Callers (e.g. the HTTP layer) translate this into a structured client error
    instead of leaking a 500.
    """

# ``ocr`` is imported lazily inside ``load_pdf`` to avoid importing the OCR
# stack unless a rasterized page actually needs it.

# Below this many non-whitespace characters, a page is treated as rasterized
# (image-only) and we rely on the vision model rather than the text layer.
_RASTER_TEXT_THRESHOLD = 20

# Render DPI for the page image handed to the vision model.
_RENDER_DPI = 150

# Maximum number of consecutive words a single value may span.
_MAX_SPAN = 10

Box = Tuple[float, float, float, float]


@dataclass(frozen=True)
class Word:
    """A word from the text layer, in PyMuPDF top-left-origin points."""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass
class LoadedPage:
    page_number: int  # 1-based
    text: str
    width: float
    height: float
    image_png: bytes
    is_rasterized: bool
    words: List[Word] = field(default_factory=list)
    ocr_used: bool = False

    def data_uri(self) -> str:
        return to_data_uri(self.image_png)


@dataclass
class LoadedDocument:
    document_id: str
    pages: List[LoadedPage] = field(default_factory=list)

    @property
    def is_rasterized(self) -> bool:
        """True if every page lacks a usable text layer."""
        return bool(self.pages) and all(p.is_rasterized for p in self.pages)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def all_text(self) -> str:
        """Text-layer text plus OCR-recovered text (for the injection scan).

        On image-only pages the native text layer is sparse, so embedded
        instructions only surface through OCR. Text-PDF pages already have their
        words in ``text``, so OCR text is appended only when OCR was actually
        used (``ocr_used``), avoiding duplication.
        """
        parts: List[str] = []
        for p in self.pages:
            parts.append(p.text)
            if p.ocr_used and p.words:
                parts.append(" ".join(w.text for w in p.words))
        return "\n".join(parts)

    def page(self, page_number: int) -> Optional[LoadedPage]:
        for p in self.pages:
            if p.page_number == page_number:
                return p
        return None


def to_data_uri(png_bytes: bytes) -> str:
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _open(source: Union[str, Path, bytes]) -> "fitz.Document":
    if isinstance(source, (bytes, bytearray)) and not bytes(source):
        raise PdfLoadError("empty document: no bytes to parse")
    try:
        if isinstance(source, (bytes, bytearray)):
            return fitz.open(stream=bytes(source), filetype="pdf")
        return fitz.open(str(source))
    except PdfLoadError:
        raise
    except Exception as exc:  # PyMuPDF raises assorted errors on bad input
        raise PdfLoadError(f"could not open source as PDF: {exc}") from exc


def load_pdf(
    source: Union[str, Path, bytes],
    document_id: str,
    ocr_engine=None,
) -> LoadedDocument:
    """Load a PDF into a :class:`LoadedDocument`. Renders each page to PNG.

    When a page has no usable text layer (rasterized) and ``ocr_engine`` is
    provided, OCR recovers line-level word boxes (converted to PDF points) so
    values can still be located on the page.
    """
    doc = _open(source)
    try:
        pages: List[LoadedPage] = []
        for index in range(doc.page_count):
            page = doc.load_page(index)
            text = page.get_text("text") or ""
            rect = page.rect
            page_width = float(rect.width)
            page_height = float(rect.height)
            pix = page.get_pixmap(dpi=_RENDER_DPI)
            png = pix.tobytes("png")
            is_rasterized = len(text.strip()) < _RASTER_TEXT_THRESHOLD

            words = [Word(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
            ocr_used = False

            if is_rasterized and ocr_engine is not None and pix.width:
                ocr_words = _ocr_words_to_points(
                    ocr_engine, png, page_width, float(pix.width)
                )
                if ocr_words:
                    words = ocr_words
                    ocr_used = True

            pages.append(
                LoadedPage(
                    page_number=index + 1,
                    text=text,
                    width=page_width,
                    height=page_height,
                    image_png=png,
                    is_rasterized=is_rasterized,
                    words=words,
                    ocr_used=ocr_used,
                )
            )
        return LoadedDocument(document_id=document_id, pages=pages)
    finally:
        doc.close()


def _ocr_words_to_points(ocr_engine, png: bytes, page_width: float, image_width: float) -> List[Word]:
    """Run OCR and convert pixel boxes (top-left origin) to PDF-point words."""
    try:
        recognized = ocr_engine.recognize(png)
    except Exception:  # noqa: BLE001 - OCR is best-effort
        return []
    if image_width <= 0:
        return []
    scale = page_width / image_width  # points per pixel
    return [
        Word(w.x0 * scale, w.y0 * scale, w.x1 * scale, w.y1 * scale, w.text)
        for w in recognized
    ]


def _numeric_candidates(value: str) -> List[str]:
    try:
        number = float(value.replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return []
    variants: List[str] = []
    if number == int(number):
        whole = int(number)
        variants += [
            str(whole),
            f"{whole:,}",
            f"${whole:,}",
            f"{whole:,}.00",
            f"${whole:,}.00",
            f"{whole}.00",
        ]
    else:
        variants += [
            f"{number:.2f}",
            f"{number:,.2f}",
            f"${number:,.2f}",
            f"${number:.2f}",
            str(number),
        ]
    return variants


def _search_candidates(display_value, normalized_value) -> List[str]:
    """Ordered, de-duplicated list of literal strings to search for on a page."""
    candidates: List[str] = []

    def add(item) -> None:
        if item is None:
            return
        text = str(item).strip()
        if text and text not in candidates:
            candidates.append(text)

    add(display_value)
    add(normalized_value)
    for source in (display_value, normalized_value):
        if source is None:
            continue
        for variant in _numeric_candidates(str(source)):
            add(variant)
    return candidates


def _norm(text: str) -> str:
    return "".join(str(text).split()).lower()


def _union_box(words: Sequence[Word], page_height: float) -> Box:
    x0 = min(w.x0 for w in words)
    y0 = min(w.y0 for w in words)
    x1 = max(w.x1 for w in words)
    y1 = max(w.y1 for w in words)
    # Convert top-left origin (y down) -> bottom-left origin (y up).
    return (
        round(x0, 2),
        round(page_height - y1, 2),
        round(x1, 2),
        round(page_height - y0, 2),
    )


def _match_span(words: Sequence[Word], target: str) -> Optional[Sequence[Word]]:
    """Exact match: a contiguous run of words whose text equals ``target``."""
    target_norm = _norm(target)
    if not target_norm:
        return None
    n = len(words)
    for i in range(n):
        joined = ""
        for j in range(i, min(i + _MAX_SPAN, n)):
            joined += _norm(words[j].text)
            if joined == target_norm:
                return words[i : j + 1]
            if len(joined) > len(target_norm):
                break
    return None


def _match_substring(word: Word, target: str, page_height: float) -> Optional[Box]:
    """Proportional sub-box when ``target`` is a substring of a word/line.

    Used for line-level OCR segments: estimate the horizontal extent of the
    value within the line by character position. Approximate but far better
    than a whole-page fallback.
    """
    line_norm = _norm(word.text)
    target_norm = _norm(target)
    if not target_norm or target_norm not in line_norm:
        return None
    start = line_norm.index(target_norm)
    end = start + len(target_norm)
    span = max(len(line_norm), 1)
    line_w = word.x1 - word.x0
    x0 = word.x0 + line_w * (start / span)
    x1 = word.x0 + line_w * (end / span)
    return (
        round(x0, 2),
        round(page_height - word.y1, 2),
        round(x1, 2),
        round(page_height - word.y0, 2),
    )


def locate_value_box(
    page: LoadedPage,
    display_value,
    normalized_value=None,
) -> Optional[Box]:
    """Locate a value on a page and return a bottom-left-origin PDF-point box.

    Tries an exact multi-word match first (native text layer), then a
    proportional substring match within a single word/line (OCR segments).
    Returns ``None`` when the page has no words or the value is not found.
    Never raises.
    """
    if not page.words:
        return None

    candidates = _search_candidates(display_value, normalized_value)

    for candidate in candidates:
        span = _match_span(page.words, candidate)
        if span:
            return _union_box(span, page.height)

    for candidate in candidates:
        for word in page.words:
            box = _match_substring(word, candidate, page.height)
            if box is not None:
                return box
    return None
