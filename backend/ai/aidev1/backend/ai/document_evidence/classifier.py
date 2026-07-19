"""B1: document classification engine.

Classifies a loaded document into one of the five organizer types (or
``unknown``) using the injected :class:`VisionLLM` over page text + image, with
a deterministic keyword fallback when the model is unavailable or unsure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from backend.ai.contracts.extraction_contract import DocumentType
from backend.ai.document_evidence import prompts
from backend.ai.document_evidence.llm import LLMError
from backend.ai.document_evidence.llm_openai import build_multimodal_messages
from backend.ai.document_evidence.pdf_loader import LoadedDocument

__all__ = ["ClassificationResult", "classify", "classify_by_text"]


@dataclass(frozen=True)
class ClassificationResult:
    document_type: DocumentType
    confidence: float


# Ordered keyword heuristics (first match wins). Used as a fallback only.
_KEYWORDS = (
    ("pay_stub", ("pay stub", "gross pay", "net pay", "pay period", "hourly rate")),
    ("benefit_letter", ("benefit", "monthly benefit", "award letter", "assistance")),
    ("employment_letter", ("employment", "employer", "verification of employment", "to whom it may concern")),
    ("gig_statement", ("gig", "platform", "earnings statement", "payout", "rideshare")),
    ("application_summary", ("application", "household size", "applicant")),
)


def classify_by_text(text: str) -> DocumentType:
    """Best-effort keyword classification. Returns ``UNKNOWN`` if no match."""
    haystack = (text or "").lower()
    for type_value, keywords in _KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return DocumentType(type_value)
    return DocumentType.UNKNOWN


def _coerce_type(raw) -> DocumentType:
    try:
        return DocumentType(str(raw).strip().lower())
    except ValueError:
        return DocumentType.UNKNOWN


def classify(document: LoadedDocument, llm) -> ClassificationResult:
    """Classify ``document`` using ``llm`` with a keyword fallback.

    Never raises: on model failure it falls back to keyword classification with
    reduced confidence.
    """
    first = document.pages[0] if document.pages else None
    page_text = first.text if first else ""
    image_present = bool(first and first.is_rasterized)

    text_messages = prompts.build_classify_prompt(page_text, image_present)
    image_uri = first.data_uri() if (first and image_present) else None
    messages = build_multimodal_messages(text_messages, image_uri)

    try:
        result = llm.complete_json(messages, {"type": "object"})
        doc_type = _coerce_type(result.get("document_type"))
        confidence = float(result.get("confidence", 0.5))
        if doc_type is DocumentType.UNKNOWN:
            fallback = classify_by_text(document.full_text)
            if fallback is not DocumentType.UNKNOWN:
                return ClassificationResult(fallback, min(confidence, 0.5))
        return ClassificationResult(doc_type, max(0.0, min(confidence, 1.0)))
    except (LLMError, ValueError, TypeError, AttributeError):
        fallback = classify_by_text(document.full_text)
        confidence = 0.5 if fallback is not DocumentType.UNKNOWN else 0.2
        return ClassificationResult(fallback, confidence)
