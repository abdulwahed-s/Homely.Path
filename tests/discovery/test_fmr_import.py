from datetime import datetime, timezone

import pandas as pd

from scripts.import_fmr_firestore import (
    build_fmr_location_map,
    load_fmr_documents,
)


def test_fmr_import_uses_actual_columns_and_preserves_geographic_codes(tmp_path):
    path = tmp_path / "fmr.xlsx"
    pd.DataFrame(
        [
            {
                "stusps": "MA",
                "state": 25,
                "hud_area_code": "METRO14460MM1120",
                "countyname": "Suffolk County",
                "county_town_name": "Boston city",
                "metro": 1,
                "hud_area_name": "Boston HUD Metro FMR Area",
                "fips": 2502507000,
                "pop2023": 1,
                "fmr_0": 2100,
                "fmr_1": 2350,
                "fmr_2": 2635,
                "fmr_3": 3190,
                "fmr_4": 3510,
            }
        ]
    ).to_excel(path, sheet_name="FY26_FMRs_revised", index=False)
    imported_at = datetime(2026, 7, 19, tzinfo=timezone.utc)

    documents = load_fmr_documents(path, imported_at=imported_at)
    document_id, payload = documents[0]

    assert document_id == "2026_2502507000"
    assert payload["county_fips"] == "25025"
    assert payload["bedroom_2"] == 2635
    assert payload["effective_date"] == "2026-05-21"
    assert payload["source_imported_at"] == imported_at

    locality, county = build_fmr_location_map(documents)
    assert locality[("MA", "boston")] == "2502507000"
    assert county["25025"] == "2502507000"
