"""HTTP surface for the RealDoor AI services (all five agent endpoints).

One mountable FastAPI app exposes every AI-owned route so the service can be
deployed standalone (full-stack calls these over HTTP):

AI Developer 1 — Document Evidence + Profile Reconciliation
- ``POST /internal/ai/extract``   -> Document Evidence Agent -> ExtractionResponse
- ``POST /internal/ai/reconcile`` -> Profile Reconciliation Agent -> conflicts

AI Developer 2 — Rules & Chat + Readiness + Safety
- ``POST /internal/ai/ask``          -> Rules & Chat Agent (grounded Q&A + citation/effective-date)
- ``POST /internal/ai/readiness``    -> Readiness Agent (checklist + status + next steps)
- ``POST /internal/ai/safety-check`` -> Safety & Report Agent (final gate)

Note (item 2): citation / rule-version / effective-date retrieval for the
calc-view explanation is **folded into /ask** (via the THRESHOLD / EFFECTIVE_DATE
intents, which return rule citations with ``rule_id`` + ``effective_date``).
There is no separate citation endpoint.

Run modes for the extract route:
- default (production): the real OpenAI vision model is built lazily on first
  request (needs ``OPENAI_API_KEY``).
- ``gold_mode=True`` (test/offline): a gold-backed fake model answers
  classification/extraction so the *real* pipeline runs deterministically with
  no API key. The gold record is selected per request by ``document_id`` (or the
  uploaded file name).

Build the app with :func:`create_app`. Dependencies (vision model, OCR) are
injectable so tests can supply fakes.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.ai import auth

logger = logging.getLogger("realdoor.ai")

from contracts.extraction_contract import (
    ActivityEvent,
    DocumentExtractionResult,
    ExtractionResponse,
    SourceBox,
)
from backend.ai.document_evidence.agent import DocumentEvidenceAgent
from backend.ai.document_evidence.llm import LLMError
from backend.ai.document_evidence.pdf_loader import PdfLoadError
from backend.ai.profile_reconciliation.agent import ReconciliationAgent
from backend.ai.rules_chat.api import router as rules_chat_router
from backend.discovery.api import router as discovery_router

__all__ = [
    "create_app",
    "ReconcileRequest",
    "ReconcileResponse",
    "ConflictOut",
    "AskBody",
]


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
    # Required when Firebase auth is enabled: must equal the caller's uid.
    session_id: Optional[str] = None


class ReconcileResponse(BaseModel):
    conflicts: List[ConflictOut]
    activity_events: List[ActivityEvent]


class AskBody(BaseModel):
    """Body for ``/internal/ai/ask``: the chat request plus its session context."""

    request: Dict[str, Any]
    context: Dict[str, Any]


def _payload_session_id(payload: Dict[str, Any]) -> Optional[str]:
    """Best-effort ``session_id`` lookup for the free-form JSON payloads.

    Readiness / safety-check accept arbitrary dicts, so the session may live at
    the top level or inside a nested ``context`` object. Full-stack callers must
    include it (top-level or in context) for these routes when auth is enabled.
    """
    if not isinstance(payload, dict):
        return None
    top = payload.get("session_id")
    if top:
        return top
    context = payload.get("context")
    if isinstance(context, dict):
        return context.get("session_id")
    return None


def create_app(
    llm=None,
    ocr_engine=None,
    *,
    gold_mode: bool = False,
    pack_root: Optional[str] = None,
) -> FastAPI:
    """Create the FastAPI app exposing all five AI endpoints.

    ``llm``/``ocr_engine`` are injectable for tests. When ``llm`` is omitted and
    ``gold_mode`` is ``False`` the real OpenAI vision model is built lazily on
    the first extract request (so the app imports without an API key present).

    When ``gold_mode`` is ``True`` the extract route answers with a gold-backed
    fake model keyed on ``document_id`` (offline, no key required). The other
    routes are model-independent and behave identically in both modes.
    """
    app = FastAPI(title="RealDoor AI Service", version="1.1")

    # CORS for the future full-stack website (and local Postman/curl). Set
    # REALDOOR_CORS_ORIGINS to a comma-separated allowlist in production
    # (e.g. "https://app.example.com,http://localhost:3000"). Default "*" is
    # fine for the hackathon / internal service until FS has a fixed origin.
    cors_raw = os.environ.get("REALDOOR_CORS_ORIGINS", "*").strip()
    allow_origins = (
        ["*"]
        if cors_raw == "*"
        else [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(discovery_router)
    app.include_router(rules_chat_router)
    app.state.chat_pack_root = pack_root

    # Firebase ID-token verification for every /internal/ai/* route. The
    # `auth.firebase_user` dependency reads `Authorization: Bearer <token>`,
    # verifies it with the Firebase Admin SDK, and each route enforces that the
    # session belongs to the authenticated user. Auth is auto-enabled when
    # Firebase credentials are configured (see backend/ai/auth.py); with no
    # credentials (offline gold / CI) it is a no-op so tests keep passing.
    @app.exception_handler(auth.AuthError)
    async def _auth_error_handler(_request: Request, exc: auth.AuthError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "detail": exc.detail},
            headers=(
                {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
            ),
        )

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        """Ensure every request leaves a line in Render live logs."""
        started = time.perf_counter()
        logger.info("→ %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("✗ %s %s crashed", request.method, request.url.path)
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "← %s %s → %s (%.0f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    state: Dict[str, Any] = {
        "llm": llm,
        "ocr": ocr_engine,
        "ocr_init": ocr_engine is not None,
        "gold_index": None,
    }

    def _get_agent() -> DocumentEvidenceAgent:
        if state["llm"] is None:
            from backend.ai.document_evidence.factory import build_vision_llm

            logger.info("Building OpenAI vision client (first extract)")
            state["llm"] = build_vision_llm()
        if not state["ocr_init"]:
            from backend.ai.document_evidence.ocr import build_ocr_engine

            # Lazy proxy: does NOT load ONNX until a rasterized page needs OCR.
            # Eager RapidOCR init was OOM-killing small Render instances on the
            # first extract even for text PDFs that never use OCR.
            state["ocr"] = build_ocr_engine(lazy=True)
            state["ocr_init"] = True
        return DocumentEvidenceAgent(state["llm"], ocr_engine=state["ocr"])

    def _gold_index() -> Dict[str, Any]:
        if state["gold_index"] is None:
            from backend.ai.document_evidence.env_config import find_organizer_pack

            pack = Path(pack_root) if pack_root else find_organizer_pack()
            if pack is None:
                raise FileNotFoundError("organizer_pack not found for gold_mode")
            gold_path = pack / "synthetic_documents" / "gold" / "document_gold.jsonl"
            index: Dict[str, Any] = {}
            for line in gold_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                index[record["document_id"]] = record
                if record.get("file_name"):
                    index[record["file_name"]] = record
            state["gold_index"] = index
        return state["gold_index"]

    def _gold_agent(document_id: str, filename: Optional[str]) -> Optional[DocumentEvidenceAgent]:
        from backend.ai.document_evidence.tests.fakes.gold_llm import GoldBackedLLM

        index = _gold_index()
        record = (
            index.get(document_id)
            or (index.get(filename) if filename else None)
            or index.get(str(document_id).upper())
        )
        if record is None:
            return None
        return DocumentEvidenceAgent(GoldBackedLLM(record))

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "mode": "gold" if gold_mode else "openai"}

    # ------------------------------------------------------------------ AI Dev 1
    @app.post("/internal/ai/extract", response_model=ExtractionResponse)
    async def extract(
        document_id: str = Form(...),
        session_id: str = Form(...),
        file: UploadFile = File(...),
        user: Optional[Dict[str, Any]] = Depends(auth.firebase_user),
    ):
        # A user may only extract into their own session (session_id == uid).
        auth.require_session_match(user, session_id)
        content = await file.read()
        logger.info(
            "extract document_id=%s filename=%s bytes=%d gold_mode=%s",
            document_id,
            file.filename,
            len(content),
            gold_mode,
        )
        if not content:
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_DOCUMENT", "detail": "uploaded file is empty"},
            )
        if gold_mode:
            agent = _gold_agent(document_id, file.filename)
            if agent is None:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error_code": "UNKNOWN_GOLD_DOCUMENT",
                        "detail": f"no gold record for document_id={document_id!r} / file={file.filename!r}",
                    },
                )
        else:
            try:
                agent = _get_agent()
            except LLMError as exc:
                return JSONResponse(
                    status_code=503,
                    content={"error_code": "VISION_MODEL_UNAVAILABLE", "detail": str(exc)},
                )
        try:
            # Offload the blocking, CPU-heavy pipeline (PDF render + OCR + model
            # I/O) to a worker thread so the event loop stays responsive and
            # /health keeps answering during a long extract (otherwise Render's
            # health check restarts the worker mid-request -> empty 502).
            result = await run_in_threadpool(
                agent.process_document, content, document_id, session_id
            )
            return result
        except PdfLoadError as exc:
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_DOCUMENT", "detail": str(exc)},
            )
        except LLMError as exc:
            return JSONResponse(
                status_code=503,
                content={"error_code": "VISION_MODEL_UNAVAILABLE", "detail": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001 - never let extract crash to bare 502
            logger.exception("extract failed document_id=%s", document_id)
            return JSONResponse(
                status_code=500,
                content={"error_code": "EXTRACT_FAILED", "detail": str(exc)},
            )

    @app.post("/internal/ai/reconcile", response_model=ReconcileResponse)
    def reconcile(
        request: ReconcileRequest,
        user: Optional[Dict[str, Any]] = Depends(auth.firebase_user),
    ) -> ReconcileResponse:
        auth.require_session_match(user, request.session_id)
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

    # ------------------------------------------------------------------ AI Dev 2
    @app.post("/internal/ai/ask")
    def ask(
        body: AskBody,
        user: Optional[Dict[str, Any]] = Depends(auth.firebase_user),
    ):
        from backend.ai import api_adapter

        session_id = body.request.get("session_id") or body.context.get("session_id")
        auth.require_session_match(user, session_id)
        try:
            return api_adapter.answer_question(body.request, body.context, pack_root=pack_root)
        except Exception as exc:  # noqa: BLE001 - surface validation errors as 400
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_REQUEST", "detail": str(exc)},
            )

    @app.post("/internal/ai/readiness")
    def readiness(
        payload: Dict[str, Any],
        user: Optional[Dict[str, Any]] = Depends(auth.firebase_user),
    ):
        from backend.ai import api_adapter

        auth.require_session_match(user, _payload_session_id(payload))
        try:
            return api_adapter.evaluate_application(payload, pack_root=pack_root)
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_REQUEST", "detail": str(exc)},
            )

    @app.post("/internal/ai/safety-check")
    def safety_check(
        payload: Dict[str, Any],
        user: Optional[Dict[str, Any]] = Depends(auth.firebase_user),
    ):
        from backend.ai import api_adapter

        auth.require_session_match(user, _payload_session_id(payload))
        try:
            return api_adapter.validate_output(payload, pack_root=pack_root)
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=400,
                content={"error_code": "INVALID_REQUEST", "detail": str(exc)},
            )

    return app
