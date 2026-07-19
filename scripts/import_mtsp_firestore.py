"""Normalize official FY2026 MTSP income limits into Firestore."""

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
from scripts.import_fmr_firestore import normalize_locality  # noqa: E402

DEFAULT_PATH = ROOT / "data" / "hud" / "mtsp" / "FY2026_MTSP.xlsx"
SOURCE_PAGE = "https://www.huduser.gov/portal/datasets/mtsp.html"
SHEET = "MTSP2026"


def _aliases() -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {
        "geo_fips": ("fips",),
        "state": ("stusps",),
        "area_id": ("hud_area_code",),
        "area_name": ("hud_area_name",),
        "locality_name": ("county_town_name",),
        "median": ("median2026",),
        "hera_type": ("HERA_Lim_type26",),
    }
    for size in range(1, 9):
        aliases[f"limit50_{size}"] = (f"lim50_26p{size}",)
        aliases[f"limit60_{size}"] = (f"Lim60_26p{size}",)
    return aliases


def _load_frame(path: Path):
    frame = read_hud_excel(path, sheet_name=SHEET, dtype=str)
    return frame, resolve_columns(frame.columns, _aliases())


def load_mtsp_documents(
    path: Path = DEFAULT_PATH,
    *,
    imported_at: datetime | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    frame, columns = _load_frame(path)
    timestamp = imported_at or datetime.now(timezone.utc)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in frame.to_dict(orient="records"):
        area_id = clean_string(row.get(columns["area_id"]))
        if area_id:
            grouped.setdefault(area_id, []).append(row)

    documents: list[tuple[str, dict[str, Any]]] = []
    for area_id, rows in grouped.items():
        first = rows[0]
        states = sorted(
            {
                state.upper()
                for row in rows
                if (state := clean_string(row.get(columns["state"])))
            }
        )
        area_name = clean_string(first.get(columns["area_name"]))
        if not states or not area_name:
            continue
        payload = {
            "area_id": area_id,
            "area_name": area_name,
            "state": states[0],
            "states": states,
            "fiscal_year": 2026,
            "median_family_income": clean_float(first.get(columns["median"])),
            "limits_50_percent": {
                str(size): clean_float(first.get(columns[f"limit50_{size}"]))
                for size in range(1, 9)
            },
            # Standard limits only. HERA-specific columns are intentionally not
            # substituted based merely on property geography.
            "limits_60_percent": {
                str(size): clean_float(first.get(columns[f"limit60_{size}"]))
                for size in range(1, 9)
            },
            "hera_special": any(
                (clean_string(row.get(columns["hera_type"])) or "").casefold()
                == "special"
                for row in rows
            ),
            "effective_date": "2026-05-01",
            "source_dataset": "HUD_MTSP",
            "source_imported_at": timestamp,
        }
        documents.append((f"2026_{area_id}", payload))
    return documents


def build_mtsp_location_map(
    path: Path = DEFAULT_PATH,
) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    frame, columns = _load_frame(path)
    locality_map: dict[tuple[str, str], str] = {}
    county_candidates: dict[str, set[str]] = {}
    for row in frame.to_dict(orient="records"):
        area_id = clean_string(row.get(columns["area_id"]))
        state = clean_string(row.get(columns["state"]))
        geo_fips = clean_code(row.get(columns["geo_fips"]), width=10)
        if not area_id or not state or not geo_fips:
            continue
        state = state.upper()
        locality = normalize_locality(row.get(columns["locality_name"]))
        if locality:
            locality_map[(state, locality)] = area_id
        county_candidates.setdefault(geo_fips[:5], set()).add(area_id)
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

    documents = load_mtsp_documents(args.path)
    if args.dry_run:
        print(f"Validated {len(documents)} MTSP areas from {args.path}")
        return 0

    db = get_firestore_client()
    count = write_documents(
        db, collection_name="mtsp_references", documents=documents
    )
    write_dataset_version(
        db,
        document_id="HUD_MTSP_2026",
        dataset_name="HUD_MTSP",
        source_file=args.path,
        source_page=SOURCE_PAGE,
        fiscal_year=2026,
        record_count=count,
    )
    print(f"Imported {count} MTSP references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
