"""Firebase ID-token verification for the internal AI HTTP surface.

The full-stack website calls the ``/internal/ai/*`` routes on behalf of a
signed-in user. Each request must carry that user's Firebase ID token as
``Authorization: Bearer <token>``. This module provides:

- Lazy Firebase Admin SDK initialization (:func:`get_firebase_app`).
- A reusable token verifier (:func:`verify_bearer_token`) that maps auth
  failures to a structured :class:`AuthError` (HTTP 401).
- A FastAPI dependency (:func:`firebase_user`) that resolves the decoded token
  from the ``Authorization`` header, and returns ``None`` when enforcement is
  disabled (so tests / offline gold runs work without credentials).
- :func:`require_session_match` to enforce that the caller may only act on their
  own session (``session_id == decoded_token["uid"]``, HTTP 403 otherwise).

Enforcement is *auto-enabled* whenever Firebase credentials are configured in
the environment, and can be forced on/off with ``REALDOOR_AUTH_ENABLED``. This
keeps the deterministic gold/offline test suite (which has no credentials)
working while making a properly-configured deploy secure by default.

Credential resolution order (first hit wins):
    1. ``FIREBASE_SERVICE_ACCOUNT_JSON``        inline service-account JSON
    2. ``FIREBASE_CREDENTIALS_JSON``            legacy inline JSON alias
    3. ``FIREBASE_CREDENTIALS_FILE``            path to a service-account JSON
    4. ``GOOGLE_APPLICATION_CREDENTIALS``       path (SDK default env var)
    5. Application Default Credentials          (GCP metadata / gcloud login)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, Optional

from fastapi import Header

logger = logging.getLogger("realdoor.ai.auth")

__all__ = [
    "AuthError",
    "is_enabled",
    "get_firebase_app",
    "verify_bearer_token",
    "firebase_user",
    "require_session_match",
]

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}

# Env vars that, when present, imply Firebase auth should be enforced.
_CREDENTIAL_ENV_VARS = (
    "FIREBASE_SERVICE_ACCOUNT_JSON",
    "FIREBASE_CREDENTIALS_JSON",
    "FIREBASE_CREDENTIALS_FILE",
    "GOOGLE_APPLICATION_CREDENTIALS",
)

_init_lock = threading.Lock()
_firebase_app: Any = None


class AuthError(Exception):
    """Structured auth failure carried to a JSON error response.

    Registered on the app via an exception handler so the body matches the
    rest of the service (``{"error_code": ..., "detail": ...}``).
    """

    def __init__(self, status_code: int, error_code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail


def is_enabled() -> bool:
    """Whether Firebase ID-token enforcement is active for this process.

    ``REALDOOR_AUTH_ENABLED`` (truthy/falsy) is an explicit override. Otherwise
    enforcement turns on automatically when any Firebase credential env var is
    set, so local/offline gold runs stay open while real deploys are locked.
    """
    override = os.environ.get("REALDOOR_AUTH_ENABLED")
    if override is not None:
        value = override.strip().lower()
        if value in _TRUTHY:
            return True
        if value in _FALSY:
            return False
    return any(os.environ.get(name) for name in _CREDENTIAL_ENV_VARS)


def _load_credentials():
    from firebase_admin import credentials

    inline = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get(
        "FIREBASE_CREDENTIALS_JSON"
    )
    if inline:
        try:
            return credentials.Certificate(json.loads(inline))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthError(
                500,
                "AUTH_MISCONFIGURED",
                f"Firebase service-account JSON is invalid: {exc}",
            ) from exc

    path = os.environ.get("FIREBASE_CREDENTIALS_FILE") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if path:
        return credentials.Certificate(path)

    # Application Default Credentials (GCP runtime / `gcloud auth`).
    return credentials.ApplicationDefault()


def get_firebase_app():
    """Return the initialized Firebase Admin app, creating it once, lazily."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    with _init_lock:
        if _firebase_app is not None:
            return _firebase_app
        try:
            import firebase_admin
        except ImportError as exc:  # pragma: no cover - depends on deploy env
            raise AuthError(
                500,
                "AUTH_MISCONFIGURED",
                "firebase-admin is not installed but Firebase auth is enabled.",
            ) from exc
        try:
            # Reuse a default app if one was already initialized elsewhere.
            _firebase_app = firebase_admin.get_app()
        except ValueError:
            try:
                _firebase_app = firebase_admin.initialize_app(_load_credentials())
            except AuthError:
                raise
            except Exception as exc:  # noqa: BLE001 - config/credential failure
                raise AuthError(
                    500,
                    "AUTH_MISCONFIGURED",
                    f"could not initialize Firebase Admin SDK: {exc}",
                ) from exc
        return _firebase_app


def verify_bearer_token(authorization: Optional[str]) -> Dict[str, Any]:
    """Verify an ``Authorization: Bearer <Firebase ID token>`` header.

    Returns the decoded token claims on success. Raises :class:`AuthError`
    (HTTP 401) for a missing, malformed, expired, revoked or otherwise invalid
    token.
    """
    if not authorization or not authorization.strip():
        raise AuthError(401, "UNAUTHORIZED", "missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.strip().lower() != "bearer" or not token.strip():
        raise AuthError(
            401, "UNAUTHORIZED", "expected 'Authorization: Bearer <token>'"
        )

    get_firebase_app()
    from firebase_admin import auth as firebase_auth

    try:
        return firebase_auth.verify_id_token(token.strip())
    except AuthError:
        raise
    except Exception as exc:  # noqa: BLE001 - invalid/expired/revoked token, etc.
        logger.info("Firebase ID token rejected: %s", exc)
        raise AuthError(401, "UNAUTHORIZED", "invalid or expired Firebase ID token") from exc


async def firebase_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: decoded Firebase token, or ``None`` if auth is off.

    Attach with ``Depends(firebase_user)``. When enforcement is disabled the
    dependency is a no-op and downstream ``require_session_match`` calls skip.
    """
    if not is_enabled():
        return None
    return verify_bearer_token(authorization)


def require_session_match(
    decoded: Optional[Dict[str, Any]], session_id: Optional[str]
) -> None:
    """Enforce ``session_id == decoded_token["uid"]``.

    No-op when ``decoded`` is ``None`` (auth disabled). Raises HTTP 403 when the
    session does not belong to the authenticated user, and HTTP 401 if the token
    is somehow missing a uid.
    """
    if decoded is None:
        return
    uid = decoded.get("uid")
    if not uid:
        raise AuthError(401, "UNAUTHORIZED", "token is missing a uid claim")
    if not session_id:
        raise AuthError(
            403,
            "SESSION_FORBIDDEN",
            "session_id is required and must match the authenticated user",
        )
    if session_id != uid:
        raise AuthError(
            403,
            "SESSION_FORBIDDEN",
            "session_id does not match the authenticated user",
        )
