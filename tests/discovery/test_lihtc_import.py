from datetime import datetime, timezone

from scripts.import_lihtc_firestore import ALIASES, normalize_lihtc_row


def test_lihtc_normalization_preserves_nulls_codes_and_unknown_availability():
    columns = {field: aliases[0] for field, aliases in ALIASES.items()}
    row = {
        "hud_id": "MA-000123",
        "project": " Harbor View ",
        "proj_add": None,
        "proj_cty": "Boston",
        "proj_st": "ma",
        "proj_zip": 2120.0,
        "st2020": 25.0,
        "cnty2020": 25.0,
        "fips2020": None,
        "latitude": 42.33,
        "longitude": -71.09,
        "n_units": None,
        "li_units": "",
        "yr_pis": 2018,
        "type": 1,
    }
    imported_at = datetime(2026, 7, 19, tzinfo=timezone.utc)

    result = normalize_lihtc_row(
        row,
        columns,
        fmr_locality_map={("MA", "boston"): "2502507000"},
        mtsp_locality_map={("MA", "boston"): "METRO14460M14460"},
        county_names={"25025": "Suffolk County"},
        imported_at=imported_at,
    )

    assert result["property_name"] == "Harbor View"
    assert result["address"] is None
    assert result["zip_code"] == "02120"
    assert result["county_fips"] == "25025"
    assert result["total_units"] is None
    assert result["low_income_units"] is None
    assert result["fmr_area_id"] == "2502507000"
    assert result["mtsp_area_id"] == "METRO14460M14460"
    assert result["availability_status"] == "UNKNOWN"
    assert result["source_imported_at"] == imported_at


def test_invalid_coordinates_and_sentinel_year_become_null():
    columns = {field: aliases[0] for field, aliases in ALIASES.items()}
    row = {column: None for column in columns.values()}
    row.update(
        {
            "hud_id": "MA-2",
            "proj_st": "MA",
            "proj_cty": "Boston",
            "latitude": 1000,
            "longitude": -1000,
            "yr_pis": 9999,
        }
    )

    result = normalize_lihtc_row(row, columns)

    assert result["latitude"] is None
    assert result["longitude"] is None
    assert result["placed_in_service_year"] is None
