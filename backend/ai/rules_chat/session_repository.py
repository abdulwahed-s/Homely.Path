"""Trusted structured-session lookup for the deterministic chat endpoint."""

from __future__ import annotations

import os
from typing import Any

from backend.discovery.firebase_client import get_firestore_client


class ChatSessionRepository:
    def __init__(self, db=None, *, collection_name: str | None = None) -> None:
        self.db = db
        self.collection_name = collection_name or os.getenv(
            "CHAT_SESSION_COLLECTION", "chat_sessions"
        )

    def get_active_session(self, session_id: str) -> dict[str, Any] | None:
        db = self.db or get_firestore_client()
        snapshot = (
            db.collection(self.collection_name).document(session_id).get()
        )
        if not snapshot.exists:
            return None
        session = snapshot.to_dict() or {}
        stored_id = session.get("session_id")
        if stored_id is not None and stored_id != session_id:
            return None
        if session.get("active") is False or session.get("status") == "CLOSED":
            return None
        if not session.get("household_id"):
            return None
        session["session_id"] = session_id
        return session
