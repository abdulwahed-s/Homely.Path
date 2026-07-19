from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.discovery.api import get_property_repository, router


class Repository:
    def find_by_location(self, *, state, city=None):
        return [
            {
                "property_id": "MA-1",
                "property_name": "Public Property",
                "city": city or "Boston",
                "state": state,
                "availability_status": "UNKNOWN",
            }
        ]

    def get_fmr_reference(self, area_id):
        return None

    def get_mtsp_reference(self, area_id):
        return None


def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_property_repository] = Repository
    return TestClient(app)


def test_discovery_endpoint_returns_transparent_public_results():
    response = client().get(
        "/api/discovery/properties",
        params={"state": "ma", "city": "Boston", "bedrooms": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result_count"] == 1
    assert body["properties"][0]["availability"]["status"] == "UNKNOWN"
    assert "not eligibility" in body["disclaimer"]
    assert {"field": "bedrooms", "value": 2, "selected_by": "RENTER"} in body[
        "filters_applied"
    ]


def test_private_or_decisional_filters_are_rejected():
    response = client().get(
        "/api/discovery/properties",
        params={"state": "MA", "renter_income": 60000},
    )

    assert response.status_code == 400
    assert "renter_income" in response.json()["detail"]


def test_location_pair_and_distance_sort_are_validated():
    response = client().get(
        "/api/discovery/properties",
        params={"state": "MA", "latitude": 42.3, "sort_by": "distance"},
    )

    assert response.status_code == 422
