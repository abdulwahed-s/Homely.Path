"""Document Evidence Agent: uploaded document -> structured evidence.

Orchestrates the owned building blocks end to end and emits activity events:

    load_pdf -> injection scan -> classify -> extract/assemble fields
             -> DocumentExtractionResult -> ExtractionResponse

Pure building blocks (normalize, boxes, confidence, allowlist) and the model
port are injected; the only I/O is PDF loading and the (injected) model.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from backend.ai.contracts.extraction_contract import (
    ActivityStatus,
    DocumentExtractionResult,
    DocumentType,
    ExtractionResponse,
    SecurityFlag,
)
from backend.ai.document_evidence import extractor
from backend.ai.document_evidence.activity import (
    AGENT_DOCUMENT_EVIDENCE,
    Clock,
    SystemClock,
    make_event,
)
from backend.ai.document_evidence.classifier import classify
from backend.ai.document_evidence.injection import scan_text
from backend.ai.document_evidence.pdf_loader import load_pdf

__all__ = ["DocumentEvidenceAgent"]


class DocumentEvidenceAgent:
    """Converts a single uploaded document into structured evidence."""

    def __init__(self, llm, clock: Optional[Clock] = None, ocr_engine=None):
        self._llm = llm
        self._clock = clock or SystemClock()
        self._ocr_engine = ocr_engine

    def _event(self, action, status, metadata=None):
        return make_event(
            AGENT_DOCUMENT_EVIDENCE, action, status, metadata, clock=self._clock
        )

    def process_document(
        self,
        source: Union[str, Path, bytes],
        document_id: str,
        session_id: str,
    ) -> ExtractionResponse:
        events = []

        # 1. Load the PDF (text + raster detection + rendered image + OCR).
        document = load_pdf(source, document_id, ocr_engine=self._ocr_engine)
        events.append(
            self._event(
                "load_document",
                ActivityStatus.PASS,
                {"pages": len(document.pages), "rasterized": document.is_rasterized},
            )
        )

        # 2. Prompt-injection / adversarial scan over all text, incl. OCR
        #    (image-only pages only surface embedded instructions via OCR).
        injection = scan_text(document.all_text)
        security_flags: List[SecurityFlag] = list(injection.flags)
        events.append(
            self._event(
                "scan_injection",
                ActivityStatus.ACTION_REQUIRED if injection.flagged else ActivityStatus.PASS,
                {"flagged": injection.flagged, "matches": injection.matched_spans},
            )
        )

        # 3. Classify.
        classification = classify(document, self._llm)
        if classification.document_type is DocumentType.UNKNOWN:
            if SecurityFlag.UNSUPPORTED_DOCUMENT not in security_flags:
                security_flags.append(SecurityFlag.UNSUPPORTED_DOCUMENT)
        events.append(
            self._event(
                "classify_document",
                ActivityStatus.PASS,
                {
                    "document_type": classification.document_type.value,
                    "confidence": classification.confidence,
                },
            )
        )

        # 4. Extract allowlisted fields and assemble evidence.
        fields = extractor.extract_document(
            document,
            classification.document_type,
            self._llm,
            classification_confidence=classification.confidence,
            injection_flagged=injection.flagged,
        )
        if document.is_rasterized and not fields:
            if SecurityFlag.OCR_FAILURE not in security_flags:
                security_flags.append(SecurityFlag.OCR_FAILURE)
        events.append(
            self._event(
                "extract_fields",
                ActivityStatus.PASS if fields else ActivityStatus.ACTION_REQUIRED,
                {
                    "field_count": len(fields),
                    "manual_entry": sum(1 for f in fields if f.requires_manual_entry),
                },
            )
        )

        result = DocumentExtractionResult(
            document_id=document_id,
            document_type=classification.document_type,
            fields=fields,
            security_flags=security_flags,
        )

        return ExtractionResponse(
            session_id=session_id,
            document=result,
            activity_events=events,
        )
