"""Validate normalized HUD records locally or verify Firestore collection counts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.discovery.distance import valid_coordinates  # noqa: E402
from backend.discovery.firebase_client import get_firestore_client  # noqa: E402
from scripts.import_fmr_firestore import load_fmr_documents  # noqa: E402
from scripts.import_lihtc_firestore import load_lihtc_documents  # noqa: E402
from scripts.import_mtsp_firestore import load_mtsp_documents  # noqa: E402


def validate_local() -> tuple[dict, list[str]]:
    fmr = load_fmr_documents()
    mtsp = load_mtsp_documents()
    properties = load_lihtc_documents()
    errors: list[str] = []

    property_ids = [document_id for document_id, _ in properties]
    if len(property_ids) != len(set(property_ids)):
        errors.append("LIHTC property IDs are not unique")

    fmr_ids = {payload["area_id"] for _, payload in fmr}
    mtsp_ids = {payload["area_id"] for _, payload in mtsp}
    states = Counter()
    missing_coordinates = 0
    invalid_coordinates = 0
    missing_fmr = 0
    missing_mtsp = 0

    for document_id, payload in properties:
        states[payload["state"]] += 1
        if payload["availability_status"] != "UNKNOWN":
            errors.append(f"{document_id}: availability must be UNKNOWN")
        lat, lon = payload.get("latitude"), payload.get("longitude")
        if lat is None or lon is None:
            missing_coordinates += 1
        elif not valid_coordinates(lat, lon):
            invalid_coordinates += 1
            errors.append(f"{document_id}: invalid coordinate pair")
        fmr_id = payload.get("fmr_area_id")
        mtsp_id = payload.get("mtsp_area_id")
        if fmr_id is None:
            missing_fmr += 1
        elif fmr_id not in fmr_ids:
            errors.append(f"{document_id}: unknown FMR reference {fmr_id}")
        if mtsp_id is None:
            missing_mtsp += 1
        elif mtsp_id not in mtsp_ids:
            errors.append(f"{document_id}: unknown MTSP reference {mtsp_id}")

    summary = {
        "properties": len(properties),
        "fmr_references": len(fmr),
        "mtsp_references": len(mtsp),
        "states": dict(sorted(states.items())),
        "missing_coordinates": missing_coordinates,
        "invalid_coordinates": invalid_coordinates,
        "missing_fmr_links": missing_fmr,
        "missing_mtsp_links": missing_mtsp,
        "errors": len(errors),
    }
    return summary, errors


def validate_firestore() -> tuple[dict, list[str]]:
    db = get_firestore_client()
    collections = (
        "discovery_properties",
        "fmr_references",
        "mtsp_references",
        "dataset_versions",
    )
    counts = {
        collection: sum(1 for _ in db.collection(collection).stream())
        for collection in collections
    }
    errors = [
        f"{collection} is empty"
        for collection, count in counts.items()
        if count == 0
    ]
    return {"firestore_counts": counts, "errors": len(errors)}, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firestore", action="store_true")
    args = parser.parse_args()
    summary, errors = validate_firestore() if args.firestore else validate_local()
    print(json.dumps(summary, indent=2))
    for error in errors[:100]:
        print(f"ERROR: {error}", file=sys.stderr)
    if len(errors) > 100:
        print(f"... plus {len(errors) - 100} more errors", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
