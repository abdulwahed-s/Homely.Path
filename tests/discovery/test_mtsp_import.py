from datetime import datetime, timezone

import pandas as pd

from scripts.import_mtsp_firestore import (
    build_mtsp_location_map,
    load_mtsp_documents,
)


def mtsp_row():
    row = {
        "fips": 2502507000,
        "stusps": "MA",
        "state": 25,
        "state_name": "MASSACHUSETTS",
        "hud_area_code": "METRO14460M14460",
        "hud_area_name": "Boston HUD Metro FMR Area",
        "county": 25,
        "County_Name": "Suffolk County",
        "county_town_name": "Boston city",
        "metro": 1,
        "median2026": 164600,
        "HERA_Lim_type26": "Special",
    }
    for size in range(1, 9):
        row[f"lim50_26p{size}"] = 50000 + size
        row[f"Lim60_26p{size}"] = 60000 + size
        row[f"Lim50_HERA_26p{size}"] = 90000 + size
        row[f"Lim60_HERA_26p{size}"] = 100000 + size
    return row


def test_mtsp_import_uses_standard_not_hera_limits(tmp_path):
    path = tmp_path / "mtsp.xlsx"
    pd.DataFrame([mtsp_row()]).to_excel(
        path, sheet_name="MTSP2026", index=False
    )
    imported_at = datetime(2026, 7, 19, tzinfo=timezone.utc)

    documents = load_mtsp_documents(path, imported_at=imported_at)
    document_id, payload = documents[0]

    assert document_id == "2026_METRO14460M14460"
    assert payload["limits_50_percent"]["1"] == 50001
    assert payload["limits_60_percent"]["2"] == 60002
    assert payload["limits_60_percent"]["2"] != 100002
    assert payload["hera_special"] is True
    assert all(isinstance(key, str) for key in payload["limits_60_percent"])

    locality, county = build_mtsp_location_map(path)
    assert locality[("MA", "boston")] == "METRO14460M14460"
    assert county["25025"] == "METRO14460M14460"
