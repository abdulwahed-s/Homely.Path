"""HTTP surface for AI Developer 1's two agents.

Thin adapters — one route per owned agent — not cross-system orchestration:

- ``POST /internal/ai/extract``   -> Document Evidence Agent -> ExtractionResponse
- ``POST /internal/ai/reconcile`` -> Profile Reconciliation Agent -> conflicts

The extract route accepts an uploaded PDF (multipart) and returns the frozen
``ExtractionResponse`` contract verbatim. The reconcile route accepts the
extracted documents and returns structured conflicts (the reconciliation output
schema is AI-Dev-1-local until a shared contract is frozen — deferred E4).

Build the app with :func:`create_app`. Dependencies (vision model, OCR) are
injected so tests can supply fakes; by default the real OpenAI model and OCR
engine are used.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.ai.contracts.extraction_contract import (
    ActivityEvent,
    DocumentExtractionResult,
    ExtractionResponse,
    SourceBox,
)
from backend.ai.document_evidence.agent import DocumentEvidenceAgent
from backend.ai.document_evidence.pdf_loader import PdfLoadError
from backend.ai.profile_reconciliation.agent import ReconciliationAgent

__all__ = ["create_app", "ReconcileRequest", "ReconcileResponse", "ConflictOut"]


class ConflictOut(BaseModel):
    conflict_id: str
    code: str
    severity: str
    message: str
    document_ids: List[str]
    field_names: List[str]
    observed_values: Dict[str, Any]
    source_refs: List[SourceBox]


class ReconcileRequest(BaseModel):
    documents: List[DocumentExtractionResult]


class ReconcileResponse(BaseModel):
    conflicts: List[ConflictOut]
    activity_events: List[ActivityEvent]


def create_app(llm=None, ocr_engine=None) -> FastAPI:
    """Create the FastAPI app.

    ``llm``/``ocr_engine`` are injectable for tests. When ``llm`` is omitted the
    real OpenAI vision model is built lazily on first extract request (so the
    app can be imported without an API key present).
    """
    app = FastAPI(title="RealDoor AI Developer 1", version="1.0")
    state: Dict[str, Any] = {"llm": llm, "ocr": ocr_engine, "ocr_init": ocr_engine is not None}

    def _get_agent() -> DocumentEvidenceAgent:
        if state["llm"] is None:
            from backend.ai.document_evidence.factory import build_vision_llm

            state["llm"] = build_vision_llm()
        if not state["ocr_init"]:
            from backend.ai.document_evidence.ocr import build_ocr_engine

            state["ocr"] = build_ocr_engine()
            state["ocr_init"] = True
        return DocumentEvidenceAgent(state["llm"], ocr_engine=state["ocr"])

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/internal/ai/extract", response_model=ExtractionResponse)
    async def extract(
        document_id: str = Form(...),
        session_id: str = Form(...),
        file: UploadFile = File(...),
    ):
        content = await file.read()
        if not content:
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_DOCUMENT", "detail": "uploaded file is empty"},
            )
        agent = _get_agent()
        try:
            return agent.process_document(content, document_id, session_id)
        except PdfLoadError as exc:
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_DOCUMENT", "detail": str(exc)},
            )

    @app.post("/internal/ai/reconcile", response_model=ReconcileResponse)
    def reconcile(request: ReconcileRequest) -> ReconcileResponse:
        result = ReconciliationAgent().reconcile(request.documents)
        conflicts = [
            ConflictOut(
                conflict_id=c.conflict_id,
                code=c.code,
                severity=c.severity.value,
                message=c.message,
                document_ids=c.document_ids,
                field_names=c.field_names,
                observed_values=c.observed_values,
                source_refs=c.source_refs,
            )
            for c in result.conflicts
        ]
        return ReconcileResponse(conflicts=conflicts, activity_events=result.activity_events)

    return app
