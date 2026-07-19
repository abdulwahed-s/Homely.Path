from backend.discovery.schemas import DiscoveryQuery
from backend.discovery.service import DiscoveryService


class Repository:
    def find_by_location(self, *, state, city=None):
        assert state == "MA"
        return [
            {
                "property_id": "MA-2",
                "property_name": "Zulu Homes",
                "address": None,
                "city": "Boston",
                "state": "MA",
                "zip_code": "02120",
                "latitude": 42.36,
                "longitude": -71.06,
                "total_units": None,
                "low_income_units": 10,
                "fmr_area_id": "2502507000",
                "mtsp_area_id": "METRO14460M14460",
            },
            {
                "property_id": "MA-1",
                "property_name": "Alpha House",
                "city": "Boston",
                "state": "MA",
                "latitude": None,
                "longitude": None,
                "fmr_area_id": None,
                "mtsp_area_id": None,
            },
        ]

    def get_fmr_reference(self, area_id):
        assert area_id == "2502507000"
        return {"fiscal_year": 2026, "bedroom_2": 2635}

    def get_mtsp_reference(self, area_id):
        assert area_id == "METRO14460M14460"
        return {
            "fiscal_year": 2026,
            "limits_60_percent": {"2": 82320},
        }


def test_reference_selectors_enrich_but_do_not_filter_properties():
    result = DiscoveryService(Repository()).search(
        DiscoveryQuery(
            state="MA",
            city="Boston",
            bedrooms=2,
            household_size=2,
        )
    )

    assert result.result_count == 2
    assert [item.property_name for item in result.properties] == [
        "Alpha House",
        "Zulu Homes",
    ]
    zulu = result.properties[1]
    assert zulu.fmr_reference.amount == 2635
    assert "not property rent" in zulu.fmr_reference.label
    assert zulu.mtsp_reference.income_limit == 82320
    assert "not an eligibility" in zulu.mtsp_reference.label
    assert all(item.availability.status == "UNKNOWN" for item in result.properties)


def test_radius_filters_by_distance_without_mutating_source_records():
    result = DiscoveryService(Repository()).search(
        DiscoveryQuery(
            state="MA",
            latitude=42.3601,
            longitude=-71.0589,
            radius_miles=1,
            sort_by="distance",
        )
    )

    assert result.result_count == 1
    assert result.properties[0].property_id == "MA-2"
    assert result.properties[0].distance_miles is not None
    assert result.ordering.method == "distance"
