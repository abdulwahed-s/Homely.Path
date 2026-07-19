"""Lazy Firebase Admin client for trusted backend use."""

from __future__ import annotations

import os
import threading
from typing import Any

_lock = threading.Lock()
_client: Any = None


def get_firestore_client():
    """Return a singleton Firestore client using ADC or configured credentials."""
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        try:
            import firebase_admin
            from firebase_admin import firestore
        except ImportError as exc:  # pragma: no cover - environment configuration
            raise RuntimeError(
                "firebase-admin is required for discovery; install requirements.txt"
            ) from exc

        try:
            app = firebase_admin.get_app()
        except ValueError:
            options = {}
            project_id = os.environ.get("FIREBASE_PROJECT_ID")
            if project_id:
                options["projectId"] = project_id
            app = firebase_admin.initialize_app(options=options or None)

        _client = firestore.client(app=app)
        return _client
