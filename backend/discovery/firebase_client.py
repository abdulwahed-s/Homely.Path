"""Lazy Firebase Admin client for trusted backend use."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

_lock = threading.Lock()
_client: Any = None


def get_firestore_client():
    """Return a shared client for emulator, service-account JSON, or ADC."""
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError as exc:  # pragma: no cover - environment configuration
            raise RuntimeError(
                "firebase-admin is required for discovery; install requirements.txt"
            ) from exc

        try:
            app = firebase_admin.get_app()
        except ValueError:
            project_id = os.environ.get("FIREBASE_PROJECT_ID")
            options = {"projectId": project_id} if project_id else None

            if os.environ.get("FIRESTORE_EMULATOR_HOST"):
                from google.auth.credentials import AnonymousCredentials

                class EmulatorCredential(credentials.Base):
                    def get_credential(self):
                        return AnonymousCredentials()

                app = firebase_admin.initialize_app(
                    EmulatorCredential(),
                    options=options,
                )
            else:
                service_account_json = os.environ.get(
                    "FIREBASE_SERVICE_ACCOUNT_JSON"
                )
                if service_account_json:
                    try:
                        service_account = json.loads(service_account_json)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            "FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON."
                        ) from exc
                    credential = credentials.Certificate(service_account)
                    app = firebase_admin.initialize_app(
                        credential,
                        options=options,
                    )
                else:
                    # Uses GOOGLE_APPLICATION_CREDENTIALS locally or the
                    # attached service identity on Google Cloud.
                    app = firebase_admin.initialize_app(options=options)

        _client = firestore.client(app=app)
        return _client
