"""Normalize the revised FY2026 county-level FMR workbook into Firestore."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.discovery.firebase_client import get_firestore_client  # noqa: E402
from scripts.hud_import_common import (  # noqa: E402
    clean_code,
    clean_float,
    clean_string,
    read_hud_excel,
    resolve_columns,
    write_dataset_version,
    write_documents,
)

DEFAULT_PATH = ROOT / "data" / "hud" / "fmr" / "FY2026_FMR_County.xlsx"
SOURCE_PAGE = "https://www.huduser.gov/portal/datasets/fmr.html"
SHEET = "FY26_FMRs_revised"

ALIASES = {
    "state": ("stusps",),
    "area_id": ("fips",),
    "area_name": ("hud_area_name",),
    "county_name": ("countyname", "County_Name"),
    "locality_name": ("county_town_name",),
    "efficiency": ("fmr_0",),
    "bedroom_1": ("fmr_1",),
    "bedroom_2": ("fmr_2",),
    "bedroom_3": ("fmr_3",),
    "bedroom_4": ("fmr_4",),
}


def normalize_locality(value: Any) -> str | None:
    text = clean_string(value)
    if not text:
        return None
    lowered = text.casefold()
    for suffix in (" town city", " city", " town", " village"):
        if lowered.endswith(suffix):
            lowered = lowered[: -len(suffix)]
            break
    return lowered.strip()


def load_fmr_documents(
    path: Path = DEFAULT_PATH,
    *,
    imported_at: datetime | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    frame = read_hud_excel(path, sheet_name=SHEET, dtype=str)
    columns = resolve_columns(frame.columns, ALIASES)
    timestamp = imported_at or datetime.now(timezone.utc)
    documents: dict[str, dict[str, Any]] = {}

    for row in frame.to_dict(orient="records"):
        area_id = clean_code(row.get(columns["area_id"]), width=10)
        state = clean_string(row.get(columns["state"]))
        area_name = clean_string(row.get(columns["area_name"]))
        if not area_id or not state or not area_name:
            continue
        county_fips = area_id[:5]
        payload = {
            "area_id": area_id,
            "area_name": area_name,
            "county_fips": county_fips,
            "county_name": clean_string(row.get(columns["county_name"])),
            "locality_name": clean_string(row.get(columns["locality_name"])),
            "locality_normalized": normalize_locality(
                row.get(columns["locality_name"])
            ),
            "state": state.upper(),
            "fiscal_year": 2026,
            "efficiency": clean_float(row.get(columns["efficiency"])),
            "bedroom_1": clean_float(row.get(columns["bedroom_1"])),
            "bedroom_2": clean_float(row.get(columns["bedroom_2"])),
            "bedroom_3": clean_float(row.get(columns["bedroom_3"])),
            "bedroom_4": clean_float(row.get(columns["bedroom_4"])),
            "effective_date": "2026-05-21",
            "source_dataset": "HUD_FMR",
            "source_imported_at": timestamp,
        }
        documents[area_id] = payload
    return [(f"2026_{area_id}", payload) for area_id, payload in documents.items()]


def build_fmr_location_map(
    documents: list[tuple[str, dict[str, Any]]],
) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    locality_map: dict[tuple[str, str], str] = {}
    county_candidates: dict[str, set[str]] = {}
    for _, payload in documents:
        area_id = payload["area_id"]
        state = payload["state"]
        locality = payload.get("locality_normalized")
        if locality:
            locality_map[(state, locality)] = area_id
        county_candidates.setdefault(payload["county_fips"], set()).add(area_id)
    county_map = {
        county: next(iter(area_ids))
        for county, area_ids in county_candidates.items()
        if len(area_ids) == 1
    }
    return locality_map, county_map


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    documents = load_fmr_documents(args.path)
    if args.dry_run:
        print(f"Validated {len(documents)} FMR records from {args.path}")
        return 0

    db = get_firestore_client()
    count = write_documents(
        db, collection_name="fmr_references", documents=documents
    )
    write_dataset_version(
        db,
        document_id="HUD_FMR_2026",
        dataset_name="HUD_FMR",
        source_file=args.path,
        source_page=SOURCE_PAGE,
        fiscal_year=2026,
        record_count=count,
    )
    print(f"Imported {count} FMR references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
