import json
from pathlib import Path

import firebase_admin
import pytest
from firebase_admin import credentials, firestore

from backend.discovery import firebase_client
from scripts.bootstrap_firestore import (
    ALLOWED_COLLECTIONS,
    load_seed,
    transform_value,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def reset_firestore_client():
    firebase_client._client = None
    yield
    firebase_client._client = None


def no_default_app():
    raise ValueError("no default app")


def test_firebase_configuration_targets_homelypath_and_deny_all_rules():
    firebase_config = json.loads((ROOT / "firebase.json").read_text())
    project_config = json.loads((ROOT / ".firebaserc").read_text())
    indexes = json.loads((ROOT / "firestore.indexes.json").read_text())
    rules = (ROOT / "firestore.rules").read_text()

    assert project_config["projects"]["default"] == "homelypath"
    assert firebase_config["emulators"]["firestore"]["port"] == 8080
    assert firebase_config["emulators"]["ui"]["port"] == 4000
    assert len(indexes["indexes"]) == 2
    assert "allow read, write: if false;" in rules


def test_seed_contains_only_the_four_discovery_collections():
    collections = load_seed(ROOT / "config" / "firestore_seed.json")

    assert set(collections) == ALLOWED_COLLECTIONS
    assert collections["discovery_properties"]["TEST-001"][
        "availability_status"
    ] == "UNKNOWN"
    assert transform_value("__SERVER_TIMESTAMP__") is firestore.SERVER_TIMESTAMP


def test_client_uses_emulator_without_credentials(monkeypatch):
    app = object()
    captured = {}
    monkeypatch.setattr(firebase_admin, "get_app", no_default_app)

    def initialize_app(*args, **kwargs):
        captured["credential"] = args[0]
        captured["options"] = kwargs.get("options")
        return app

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(firestore, "client", lambda *, app: ("client", app))
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "homelypath")
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)

    client = firebase_client.get_firestore_client()

    assert client == ("client", app)
    assert captured["options"] == {"projectId": "homelypath"}
    assert captured["credential"].get_credential().token is None


def test_client_accepts_render_service_account_json(monkeypatch):
    app = object()
    certificate = object()
    captured = {}
    service_account = {"project_id": "homelypath", "private_key": "secret"}
    monkeypatch.setattr(firebase_admin, "get_app", no_default_app)
    monkeypatch.setattr(credentials, "Certificate", lambda value: certificate)

    def initialize_app(credential=None, options=None):
        captured.update(credential=credential, options=options)
        return app

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(firestore, "client", lambda *, app: ("client", app))
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "homelypath")
    monkeypatch.setenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON", json.dumps(service_account)
    )
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)

    assert firebase_client.get_firestore_client() == ("client", app)
    assert captured == {
        "credential": certificate,
        "options": {"projectId": "homelypath"},
    }


def test_invalid_render_service_account_json_is_actionable(monkeypatch):
    monkeypatch.setattr(firebase_admin, "get_app", no_default_app)
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{invalid")
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)

    with pytest.raises(RuntimeError, match="contains invalid JSON"):
        firebase_client.get_firestore_client()
