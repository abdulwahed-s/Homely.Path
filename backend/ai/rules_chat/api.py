"""Public session-scoped endpoint for deterministic rules chat."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.ai import auth
from backend.ai.rules_chat.context_builder import build_chat_context
from backend.ai.rules_chat.rule_store import RuleStore
from backend.ai.rules_chat.schemas import (
    GroundedChatRequest,
    GroundedChatResponse,
)
from backend.ai.rules_chat.service import GroundedRulesChatService
from backend.ai.rules_chat.session_repository import ChatSessionRepository
from backend.ai.safety.policies import detect_sensitive_question
from backend.ai.safety.validator import SafetyValidator

logger = logging.getLogger("realdoor.rules_chat")
router = APIRouter(prefix="/api/chat", tags=["rules-chat"])


def _enabled() -> bool:
    return os.getenv("CHATBOT_ENABLED", "false").casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_chat_session_repository() -> ChatSessionRepository:
    return ChatSessionRepository()


def get_grounded_chatbot(request: Request) -> GroundedRulesChatService:
    chatbot = getattr(request.app.state, "grounded_chatbot", None)
    if chatbot is None:
        from backend.ai.api_adapter import resolve_pack_root

        root = resolve_pack_root(
            getattr(request.app.state, "chat_pack_root", None)
        )
        chatbot = GroundedRulesChatService(
            rule_store=RuleStore.from_jsonl(
                root / "rules" / "rule_corpus.jsonl"
            ),
            safety_validator=SafetyValidator(),
        )
        request.app.state.grounded_chatbot = chatbot
    return chatbot


@router.post("/answer", response_model=GroundedChatResponse)
def answer_question(
    body: GroundedChatRequest,
    request: Request,
    user=Depends(auth.firebase_user),
    repository: ChatSessionRepository = Depends(
        get_chat_session_repository
    ),
    chatbot: GroundedRulesChatService = Depends(get_grounded_chatbot),
) -> GroundedChatResponse:
    if not _enabled():
        raise HTTPException(status_code=503, detail="Chatbot is disabled.")

    # Detect before any Firestore/session-result retrieval.
    sensitive = detect_sensitive_question(body.question)
    auth.require_session_match(user, body.session_id)
    if sensitive.blocked:
        response = chatbot.answer(body.question, None)
        logger.info(
            "CHAT_QUESTION intent=%s status=%s",
            response.intent,
            response.status,
        )
        return response

    session = repository.get_active_session(body.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Active session not found.",
        )

    try:
        context = build_chat_context(session)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail="Active session results are incomplete.",
        ) from exc

    response = chatbot.answer(body.question, context)
    logger.info(
        "CHAT_QUESTION intent=%s status=%s",
        response.intent,
        response.status,
    )
    return response
