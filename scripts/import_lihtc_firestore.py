"""Normalize the official public LIHTC property file into Firestore."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.discovery.firebase_client import get_firestore_client  # noqa: E402
from scripts.hud_import_common import (  # noqa: E402
    clean_code,
    clean_coordinate,
    clean_integer,
    clean_string,
    read_hud_excel,
    resolve_columns,
    write_dataset_version,
    write_documents,
)
from scripts.import_fmr_firestore import (  # noqa: E402
    DEFAULT_PATH as FMR_PATH,
    build_fmr_location_map,
    load_fmr_documents,
    normalize_locality,
)
from scripts.import_mtsp_firestore import (  # noqa: E402
    DEFAULT_PATH as MTSP_PATH,
    build_mtsp_location_map,
)

SOURCE_PAGE = "https://www.huduser.gov/portal/datasets/lihtc/property.html"
LIHTC_DIRECTORY = ROOT / "data" / "hud" / "lihtc"

ALIASES = {
    "property_id": ("hud_id", "HUD_ID"),
    "property_name": ("project", "PROJECT"),
    "address": ("proj_add", "PROJ_ADD"),
    "city": ("proj_cty", "PROJ_CTY"),
    "state": ("proj_st", "PROJ_ST"),
    "zip_code": ("proj_zip", "PROJ_ZIP"),
    "state_fips": ("st2020", "ST2020"),
    "county_fips": ("cnty2020", "CNTY2020"),
    "tract_fips": ("fips2020", "FIPS2020"),
    "latitude": ("latitude", "LAT"),
    "longitude": ("longitude", "LON"),
    "total_units": ("n_units", "N_UNITS"),
    "low_income_units": ("li_units", "LI_UNITS"),
    "placed_year": ("yr_pis", "YR_PIS"),
    "construction_type": ("type", "TYPE"),
}


def default_lihtc_path() -> Path:
    csv_path = LIHTC_DIRECTORY / "LIHTCPUB.CSV"
    xlsx_path = LIHTC_DIRECTORY / "LIHTCPUB.xlsx"
    return csv_path if csv_path.exists() else xlsx_path


def _county_fips(row: dict[str, Any], columns: dict[str, str]) -> str | None:
    state = clean_code(row.get(columns["state_fips"]), width=2)
    county = clean_code(row.get(columns["county_fips"]), width=3)
    if state and county:
        return f"{state}{county}"
    tract = clean_code(row.get(columns["tract_fips"]), width=11)
    return tract[:5] if tract and len(tract) >= 5 else None


def _valid_year(value: Any) -> int | None:
    year = clean_integer(value)
    return year if year is not None and 1900 <= year <= 2026 else None


def normalize_lihtc_row(
    row: dict[str, Any],
    column_map: dict[str, str],
    *,
    fmr_locality_map: dict[tuple[str, str], str] | None = None,
    fmr_county_map: dict[str, str] | None = None,
    mtsp_locality_map: dict[tuple[str, str], str] | None = None,
    mtsp_county_map: dict[str, str] | None = None,
    county_names: dict[str, str] | None = None,
    imported_at: datetime | None = None,
    source_version: str | None = "2024",
) -> dict[str, Any]:
    fmr_locality_map = fmr_locality_map or {}
    fmr_county_map = fmr_county_map or {}
    mtsp_locality_map = mtsp_locality_map or {}
    mtsp_county_map = mtsp_county_map or {}
    county_names = county_names or {}

    state = (clean_string(row.get(column_map["state"])) or "").upper()
    city = clean_string(row.get(column_map["city"]))
    city_normalized = normalize_locality(city)
    county_fips = _county_fips(row, column_map)
    location_key = (state, city_normalized) if state and city_normalized else None

    return {
        "property_id": clean_string(row.get(column_map["property_id"])),
        "property_name": clean_string(row.get(column_map["property_name"])),
        "address": clean_string(row.get(column_map["address"])),
        "city": city,
        "city_normalized": city.casefold() if city else None,
        "state": state or None,
        "zip_code": clean_code(row.get(column_map["zip_code"]), width=5),
        "county_name": county_names.get(county_fips) if county_fips else None,
        "county_fips": county_fips,
        "latitude": clean_coordinate(
            row.get(column_map["latitude"]), latitude=True
        ),
        "longitude": clean_coordinate(
            row.get(column_map["longitude"]), latitude=False
        ),
        "total_units": clean_integer(row.get(column_map["total_units"])),
        "low_income_units": clean_integer(
            row.get(column_map["low_income_units"])
        ),
        "placed_in_service_year": _valid_year(
            row.get(column_map["placed_year"])
        ),
        # Preserve the official code instead of inventing a label.
        "construction_type": clean_string(
            row.get(column_map["construction_type"])
        ),
        "fmr_area_id": (
            fmr_locality_map.get(location_key)
            if location_key
            else None
        )
        or (fmr_county_map.get(county_fips) if county_fips else None),
        "mtsp_area_id": (
            mtsp_locality_map.get(location_key)
            if location_key
            else None
        )
        or (mtsp_county_map.get(county_fips) if county_fips else None),
        "availability_status": "UNKNOWN",
        "source_dataset": "HUD_LIHTC",
        "source_version": source_version,
        "source_imported_at": imported_at or datetime.now(timezone.utc),
    }


def load_lihtc_documents(
    path: Path | None = None,
    *,
    fmr_path: Path = FMR_PATH,
    mtsp_path: Path = MTSP_PATH,
    source_version: str | None = "2024",
    imported_at: datetime | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    path = path or default_lihtc_path()
    if path.suffix.casefold() == ".csv":
        frame = pd.read_csv(path, low_memory=False, dtype=str)
    else:
        frame = read_hud_excel(path, sheet_name="Data", dtype=str)
    columns = resolve_columns(frame.columns, ALIASES)

    fmr_documents = load_fmr_documents(fmr_path, imported_at=imported_at)
    fmr_locality, fmr_county = build_fmr_location_map(fmr_documents)
    mtsp_locality, mtsp_county = build_mtsp_location_map(mtsp_path)
    county_names = {
        payload["county_fips"]: payload["county_name"]
        for _, payload in fmr_documents
        if payload.get("county_name")
    }
    timestamp = imported_at or datetime.now(timezone.utc)

    documents: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        payload = normalize_lihtc_row(
            row,
            columns,
            fmr_locality_map=fmr_locality,
            fmr_county_map=fmr_county,
            mtsp_locality_map=mtsp_locality,
            mtsp_county_map=mtsp_county,
            county_names=county_names,
            imported_at=timestamp,
            source_version=source_version,
        )
        property_id = payload["property_id"]
        if not property_id or not payload["state"]:
            continue
        documents[property_id] = payload
    return list(documents.items())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=None)
    parser.add_argument("--source-version", default="2024")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = args.path or default_lihtc_path()
    documents = load_lihtc_documents(
        path, source_version=args.source_version
    )
    if args.dry_run:
        print(f"Validated {len(documents)} LIHTC properties from {path}")
        return 0

    db = get_firestore_client()
    count = write_documents(
        db, collection_name="discovery_properties", documents=documents
    )
    write_dataset_version(
        db,
        document_id="HUD_LIHTC",
        dataset_name="HUD_LIHTC",
        source_file=path,
        source_page=SOURCE_PAGE,
        source_year=int(args.source_version) if args.source_version else None,
        record_count=count,
    )
    print(f"Imported {count} LIHTC properties")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
