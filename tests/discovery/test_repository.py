from backend.discovery.repository import PropertyRepository


class Snapshot:
    def __init__(self, document_id, payload=None):
        self.id = document_id
        self.payload = payload
        self.exists = payload is not None

    def to_dict(self):
        return dict(self.payload) if self.payload is not None else None


class Query:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.filters = []

    def where(self, field, operator, value):
        self.filters.append((field, operator, value))
        return self

    def stream(self):
        result = self.snapshots
        for field, _, value in self.filters:
            result = [
                snapshot
                for snapshot in result
                if snapshot.payload.get(field) == value
            ]
        return result


class Collection:
    def __init__(self, documents):
        self.documents = documents

    def where(self, field, operator, value):
        return Query(
            [Snapshot(document_id, payload) for document_id, payload in self.documents.items()]
        ).where(field, operator, value)

    def document(self, document_id):
        documents = self.documents

        class Reference:
            def get(self):
                return Snapshot(document_id, documents.get(document_id))

        return Reference()


class Db:
    def __init__(self):
        self.collections = {
            "discovery_properties": {
                "MA-1": {"state": "MA", "city_normalized": "boston"},
                "MA-2": {"state": "MA", "city_normalized": "cambridge"},
                "NY-1": {"state": "NY", "city_normalized": "boston"},
            },
            "fmr_references": {
                "2026_25025": {"area_id": "25025", "bedroom_2": 2600}
            },
            "mtsp_references": {},
        }

    def collection(self, name):
        return Collection(self.collections[name])


def test_repository_filters_state_and_normalized_city():
    repository = PropertyRepository(Db())
    results = repository.find_by_location(state="ma", city=" Boston ")

    assert results == [
        {
            "state": "MA",
            "city_normalized": "boston",
            "property_id": "MA-1",
        }
    ]


def test_repository_returns_reference_or_null():
    repository = PropertyRepository(Db())

    assert repository.get_fmr_reference("25025")["bedroom_2"] == 2600
    assert repository.get_mtsp_reference("missing") is None
    assert repository.get_fmr_reference(None) is None
