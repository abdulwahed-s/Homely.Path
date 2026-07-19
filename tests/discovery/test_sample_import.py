from datetime import datetime, timezone

import pytest

from scripts.import_discovery_samples import (
    KNOWN_PROPERTY_ID,
    LIHTC_VERSION_ID,
    MTSP_AREA_ID,
    MTSP_VERSION_ID,
    import_samples,
    load_sample_mtsp_document,
    load_sample_property_documents,
    validate_destination,
    validate_sample_documents,
    verify_sample_firestore,
)


class FakeSnapshot:
    def __init__(self, payload):
        self._payload = payload
        self.exists = payload is not None

    def to_dict(self):
        return self._payload


class FakeReference:
    def __init__(self, store, collection, document_id):
        self.store = store
        self.key = (collection, document_id)

    def set(self, payload, merge=False):
        if merge:
            current = self.store.get(self.key, {})
            self.store[self.key] = {**current, **payload}
        else:
            self.store[self.key] = dict(payload)

    def get(self):
        return FakeSnapshot(self.store.get(self.key))


class FakeCollection:
    def __init__(self, store, name):
        self.store = store
        self.name = name

    def document(self, document_id):
        return FakeReference(self.store, self.name, document_id)


class FakeBatch:
    def __init__(self):
        self.operations = []

    def set(self, reference, payload, merge=False):
        self.operations.append((reference, payload, merge))

    def commit(self):
        for reference, payload, merge in self.operations:
            reference.set(payload, merge=merge)
        self.operations.clear()


class FakeFirestore:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        return FakeCollection(self.store, name)

    def batch(self):
        return FakeBatch()


def test_bundled_samples_normalize_and_link_without_fabricated_fmr():
    imported_at = datetime(2026, 7, 19, tzinfo=timezone.utc)
    properties = dict(
        load_sample_property_documents(imported_at=imported_at)
    )
    mtsp_id, mtsp = load_sample_mtsp_document(imported_at=imported_at)

    known = properties[KNOWN_PROPERTY_ID]
    assert known["city_normalized"] == "boston"
    assert known["zip_code"] == "02115"
    assert known["fmr_area_id"] is None
    assert known["mtsp_area_id"] == MTSP_AREA_ID
    assert known["source_imported_at"] == imported_at
    assert properties["MAB00000253"]["placed_in_service_year"] is None

    assert mtsp_id == f"2026_{MTSP_AREA_ID}"
    assert mtsp["limits_60_percent"]["1"] == 72000
    assert mtsp["limits_60_percent"]["8"] == 135780
    assert validate_sample_documents(list(properties.items()), (mtsp_id, mtsp)) == []


def test_production_write_requires_explicit_confirmation(monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)

    with pytest.raises(ValueError, match="Refusing production write"):
        validate_destination(
            project_id="homelypath",
            emulator_host=None,
            allow_production_write=False,
        )

    validate_destination(
        project_id="homelypath",
        emulator_host=None,
        allow_production_write=True,
    )

    with pytest.raises(ValueError, match="cannot be used with"):
        validate_destination(
            project_id="homelypath",
            emulator_host="127.0.0.1:8080",
            allow_production_write=True,
        )


def test_production_write_rejects_credential_project_mismatch(monkeypatch):
    monkeypatch.setenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        '{"project_id": "different-project"}',
    )

    with pytest.raises(ValueError, match="does not match"):
        validate_destination(
            project_id="homelypath",
            emulator_host=None,
            allow_production_write=True,
        )


def test_import_and_deep_verification_use_expected_collections():
    properties = load_sample_property_documents()
    mtsp = load_sample_mtsp_document()
    db = FakeFirestore()

    counts = import_samples(
        db,
        properties=properties,
        mtsp_document=mtsp,
    )

    assert counts == {
        "discovery_properties": len(properties),
        "mtsp_references": 1,
        "dataset_versions": 2,
    }
    assert db.store[("dataset_versions", LIHTC_VERSION_ID)][
        "record_count"
    ] == len(properties)
    assert db.store[("dataset_versions", MTSP_VERSION_ID)][
        "record_count"
    ] == 1
    assert verify_sample_firestore(
        db,
        expected_property_ids={
            document_id for document_id, _ in properties
        },
    ) == []
