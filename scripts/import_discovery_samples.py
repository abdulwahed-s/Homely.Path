"""Import the bundled Boston discovery samples into Firestore.

This is an explicit operator command. Production writes require both the
destination project ID and ``--allow-production-write``; the web service never
runs this importer during build or startup.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.discovery.distance import valid_coordinates  # noqa: E402
from backend.discovery.firebase_client import get_firestore_client  # noqa: E402
from scripts.hud_import_common import (  # noqa: E402
    clean_code,
    clean_coordinate,
    clean_float,
    clean_integer,
    clean_string,
    write_dataset_version,
    write_documents,
)

LIHTC_PATH = ROOT / "organizer_pack" / "data" / "lihtc_boston_metro_subset.csv"
MTSP_PATH = (
    ROOT
    / "organizer_pack"
    / "data"
    / "mtsp_2026_boston_cambridge_quincy.csv"
)
LIHTC_SOURCE_PAGE = (
    "https://www.huduser.gov/portal/datasets/lihtc/property.html"
)
MTSP_SOURCE_PAGE = "https://www.huduser.gov/portal/datasets/mtsp.html"
MTSP_AREA_ID = "BOSTON-CAMBRIDGE-QUINCY-MA-NH-HMFA"
KNOWN_PROPERTY_ID = "MAB20200006"
LIHTC_VERSION_ID = "HUD_LIHTC_BOSTON_SAMPLE"
MTSP_VERSION_ID = "HUD_MTSP_2026_BOSTON_SAMPLE"


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise ValueError(f"Sample file does not exist: {path}") from exc


def _valid_year(value: Any) -> int | None:
    year = clean_integer(value)
    return year if year is not None and 1900 <= year <= 2026 else None


def load_sample_mtsp_document(
    path: Path = MTSP_PATH,
    *,
    imported_at: datetime | None = None,
) -> tuple[str, dict[str, Any]]:
    rows = _read_csv(path)
    if not rows:
        raise ValueError(f"MTSP sample is empty: {path}")

    sizes = {clean_integer(row.get("household_size")) for row in rows}
    if sizes != set(range(1, 9)):
        raise ValueError("MTSP sample must contain household sizes 1 through 8")

    fiscal_years = {clean_integer(row.get("fiscal_year")) for row in rows}
    area_names = {clean_string(row.get("hud_area")) for row in rows}
    if fiscal_years != {2026} or len(area_names) != 1 or None in area_names:
        raise ValueError("MTSP sample has inconsistent fiscal year or HUD area")

    by_size = {
        clean_integer(row["household_size"]): row
        for row in rows
    }
    first = rows[0]
    payload = {
        "area_id": MTSP_AREA_ID,
        "area_name": next(iter(area_names)),
        "state": "MA",
        "states": ["MA", "NH"],
        "fiscal_year": 2026,
        "median_family_income": clean_float(
            first.get("median_family_income")
        ),
        "limits_50_percent": {
            str(size): clean_float(
                by_size[size].get("income_limit_50_percent")
            )
            for size in range(1, 9)
        },
        "limits_60_percent": {
            str(size): clean_float(
                by_size[size].get("income_limit_60_percent")
            )
            for size in range(1, 9)
        },
        "hera_special": False,
        "effective_date": clean_string(first.get("effective_date")),
        "source_dataset": "HUD_MTSP_BOSTON_SAMPLE",
        "source_imported_at": imported_at or datetime.now(timezone.utc),
    }
    return f"2026_{MTSP_AREA_ID}", payload


def load_sample_property_documents(
    path: Path = LIHTC_PATH,
    *,
    imported_at: datetime | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    timestamp = imported_at or datetime.now(timezone.utc)
    documents: dict[str, dict[str, Any]] = {}

    for row in _read_csv(path):
        property_id = clean_string(row.get("hud_id"))
        state = (clean_string(row.get("project_state")) or "").upper()
        if not property_id or not state:
            continue
        if property_id in documents:
            raise ValueError(f"Duplicate LIHTC property ID: {property_id}")

        property_name = clean_string(row.get("project_name"))
        city = clean_string(row.get("project_city"))
        documents[property_id] = {
            "property_id": property_id,
            "property_name": property_name,
            "property_name_normalized": (
                property_name.casefold() if property_name else None
            ),
            "address": clean_string(row.get("project_address")),
            "city": city,
            "city_normalized": city.casefold() if city else None,
            "state": state,
            "zip_code": clean_code(row.get("project_zip"), width=5),
            "county_name": None,
            "county_fips": None,
            "latitude": clean_coordinate(
                row.get("latitude"), latitude=True
            ),
            "longitude": clean_coordinate(
                row.get("longitude"), latitude=False
            ),
            "total_units": clean_integer(row.get("total_units")),
            "low_income_units": clean_integer(row.get("low_income_units")),
            "placed_in_service_year": _valid_year(
                row.get("year_placed_in_service")
            ),
            "construction_type": clean_string(
                row.get("project_type_code")
            ),
            # The organizer pack contains no compatible FMR sample.
            "fmr_area_id": None,
            "mtsp_area_id": MTSP_AREA_ID,
            "availability_status": "UNKNOWN",
            "source_dataset": "HUD_LIHTC_BOSTON_SAMPLE",
            "source_version": clean_string(row.get("retrieved_utc")),
            "source_imported_at": timestamp,
            "data_quality_flags": clean_string(
                row.get("data_quality_flags")
            ),
        }

    if not documents:
        raise ValueError(f"No valid LIHTC properties found in {path}")
    if KNOWN_PROPERTY_ID not in documents:
        raise ValueError(
            f"LIHTC sample is missing known property {KNOWN_PROPERTY_ID}"
        )
    return list(documents.items())


def validate_sample_documents(
    properties: list[tuple[str, dict[str, Any]]],
    mtsp_document: tuple[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    mtsp_id, mtsp = mtsp_document
    if mtsp_id != f"2026_{MTSP_AREA_ID}":
        errors.append("MTSP document ID does not match the sample area")
    if any(mtsp["limits_60_percent"].get(str(size)) is None for size in range(1, 9)):
        errors.append("MTSP sample has missing 60 percent limits")

    for document_id, payload in properties:
        if payload.get("property_id") != document_id:
            errors.append(f"{document_id}: property ID mismatch")
        if payload.get("availability_status") != "UNKNOWN":
            errors.append(f"{document_id}: availability must be UNKNOWN")
        if payload.get("mtsp_area_id") != MTSP_AREA_ID:
            errors.append(f"{document_id}: MTSP link is missing")
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if latitude is not None or longitude is not None:
            if not valid_coordinates(latitude, longitude):
                errors.append(f"{document_id}: invalid coordinate pair")
    return errors


def validate_destination(
    *,
    project_id: str | None,
    emulator_host: str | None,
    allow_production_write: bool,
) -> None:
    if not project_id:
        raise ValueError("--project-id is required for every write")
    if emulator_host and allow_production_write:
        raise ValueError(
            "--allow-production-write cannot be used with a Firestore emulator"
        )
    if not emulator_host and not allow_production_write:
        raise ValueError(
            "Refusing production write without --allow-production-write"
        )

    inline = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if inline and not emulator_host:
        try:
            credential_project = json.loads(inline).get("project_id")
        except (AttributeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON"
            ) from exc
        if credential_project and credential_project != project_id:
            raise ValueError(
                "Service-account project does not match --project-id"
            )


def import_samples(
    db,
    *,
    properties: list[tuple[str, dict[str, Any]]],
    mtsp_document: tuple[str, dict[str, Any]],
    lihtc_path: Path = LIHTC_PATH,
    mtsp_path: Path = MTSP_PATH,
) -> dict[str, int]:
    mtsp_count = write_documents(
        db,
        collection_name="mtsp_references",
        documents=[mtsp_document],
    )
    property_count = write_documents(
        db,
        collection_name="discovery_properties",
        documents=properties,
    )
    write_dataset_version(
        db,
        document_id=MTSP_VERSION_ID,
        dataset_name="HUD_MTSP_BOSTON_SAMPLE",
        source_file=mtsp_path,
        source_page=MTSP_SOURCE_PAGE,
        fiscal_year=2026,
        record_count=mtsp_count,
    )
    write_dataset_version(
        db,
        document_id=LIHTC_VERSION_ID,
        dataset_name="HUD_LIHTC_BOSTON_SAMPLE",
        source_file=lihtc_path,
        source_page=LIHTC_SOURCE_PAGE,
        source_year=2026,
        record_count=property_count,
    )
    return {
        "discovery_properties": property_count,
        "mtsp_references": mtsp_count,
        "dataset_versions": 2,
    }


def verify_sample_firestore(
    db,
    *,
    expected_property_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    known = (
        db.collection("discovery_properties")
        .document(KNOWN_PROPERTY_ID)
        .get()
    )
    if not known.exists:
        errors.append(f"Known property {KNOWN_PROPERTY_ID} is missing")
    else:
        payload = known.to_dict() or {}
        if payload.get("city_normalized") != "boston":
            errors.append(f"{KNOWN_PROPERTY_ID}: expected Boston location")
        if payload.get("mtsp_area_id") != MTSP_AREA_ID:
            errors.append(f"{KNOWN_PROPERTY_ID}: expected MTSP link")

    missing_ids = [
        property_id
        for property_id in sorted(expected_property_ids)
        if not (
            db.collection("discovery_properties")
            .document(property_id)
            .get()
            .exists
        )
    ]
    if missing_ids:
        errors.append(
            f"{len(missing_ids)} sample properties are missing: "
            + ", ".join(missing_ids[:5])
        )

    mtsp = (
        db.collection("mtsp_references")
        .document(f"2026_{MTSP_AREA_ID}")
        .get()
    )
    if not mtsp.exists:
        errors.append("Bundled MTSP reference is missing")

    expected_versions = {
        LIHTC_VERSION_ID: len(expected_property_ids),
        MTSP_VERSION_ID: 1,
    }
    for version_id, expected_count in expected_versions.items():
        snapshot = (
            db.collection("dataset_versions").document(version_id).get()
        )
        if not snapshot.exists:
            errors.append(f"Dataset version {version_id} is missing")
            continue
        metadata = snapshot.to_dict() or {}
        if metadata.get("status") != "ACTIVE":
            errors.append(f"Dataset version {version_id} is not ACTIVE")
        if metadata.get("record_count") != expected_count:
            errors.append(
                f"Dataset version {version_id} expected {expected_count} "
                f"records, found {metadata.get('record_count')}"
            )
        if not metadata.get("checksum_sha256"):
            errors.append(f"Dataset version {version_id} has no checksum")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lihtc-path", type=Path, default=LIHTC_PATH)
    parser.add_argument("--mtsp-path", type=Path, default=MTSP_PATH)
    parser.add_argument("--project-id")
    parser.add_argument("--emulator", metavar="HOST:PORT")
    parser.add_argument("--allow-production-write", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc)
    properties = load_sample_property_documents(
        args.lihtc_path, imported_at=timestamp
    )
    mtsp_document = load_sample_mtsp_document(
        args.mtsp_path, imported_at=timestamp
    )
    errors = validate_sample_documents(properties, mtsp_document)
    if errors:
        raise SystemExit("Sample validation failed:\n- " + "\n- ".join(errors))

    print(
        f"Validated {len(properties)} properties and 1 MTSP area "
        f"for project {args.project_id or '(not selected)'}"
    )
    if args.dry_run:
        return 0

    if not args.project_id:
        raise SystemExit("--project-id is required")
    os.environ["FIREBASE_PROJECT_ID"] = args.project_id
    if args.emulator:
        os.environ["FIRESTORE_EMULATOR_HOST"] = args.emulator

    if args.verify_only:
        db = get_firestore_client()
        verify_errors = verify_sample_firestore(
            db,
            expected_property_ids={
                document_id for document_id, _ in properties
            },
        )
        if verify_errors:
            raise SystemExit(
                "Firestore verification failed:\n- "
                + "\n- ".join(verify_errors)
            )
        print("Firestore verification passed")
        return 0

    validate_destination(
        project_id=args.project_id,
        emulator_host=args.emulator or os.getenv("FIRESTORE_EMULATOR_HOST"),
        allow_production_write=args.allow_production_write,
    )
    db = get_firestore_client()
    counts = import_samples(
        db,
        properties=properties,
        mtsp_document=mtsp_document,
        lihtc_path=args.lihtc_path,
        mtsp_path=args.mtsp_path,
    )
    print(f"Imported into Firebase project {args.project_id}:")
    for collection, count in counts.items():
        print(f"- {collection}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
