"""Create and verify the four discovery collections from a synthetic seed."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebase_admin import firestore  # noqa: E402

from backend.discovery.firebase_client import get_firestore_client  # noqa: E402

ALLOWED_COLLECTIONS = {
    "discovery_properties",
    "fmr_references",
    "mtsp_references",
    "dataset_versions",
}


def transform_value(value: Any) -> Any:
    if value == "__SERVER_TIMESTAMP__":
        return firestore.SERVER_TIMESTAMP
    if isinstance(value, dict):
        return {key: transform_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [transform_value(item) for item in value]
    return value


def load_seed(
    seed_path: Path,
) -> dict[str, dict[str, dict[str, Any]]]:
    try:
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Seed file does not exist: {seed_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Seed file contains invalid JSON: {exc}") from exc

    collections = seed.get("collections")
    if not isinstance(collections, dict):
        raise SystemExit("Seed JSON requires a top-level 'collections' object.")

    unexpected = set(collections) - ALLOWED_COLLECTIONS
    if unexpected:
        raise SystemExit(f"Unexpected collections: {sorted(unexpected)}")

    malformed = [
        collection
        for collection, documents in collections.items()
        if not isinstance(documents, dict)
    ]
    if malformed:
        raise SystemExit(f"Collection values must be objects: {sorted(malformed)}")
    return collections


def write_collections(
    collections: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, int]:
    db = get_firestore_client()
    counts: dict[str, int] = {}
    batch = db.batch()
    pending_writes = 0

    for collection_name, documents in collections.items():
        counts[collection_name] = 0
        for document_id, document_data in documents.items():
            if not isinstance(document_data, dict):
                raise SystemExit(
                    f"{collection_name}/{document_id} must contain an object."
                )
            reference = db.collection(collection_name).document(document_id)
            batch.set(
                reference,
                transform_value(document_data),
                merge=True,
            )
            counts[collection_name] += 1
            pending_writes += 1
            if pending_writes >= 300:
                batch.commit()
                batch = db.batch()
                pending_writes = 0

    if pending_writes:
        batch.commit()
    return counts


def verify_collections() -> None:
    db = get_firestore_client()
    print("\nFirestore verification:")
    for collection_name in sorted(ALLOWED_COLLECTIONS):
        documents = list(db.collection(collection_name).limit(3).stream())
        document_ids = [document.id for document in documents]
        print(
            f"- {collection_name}: {len(documents)} sample document(s) "
            f"{document_ids}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        type=Path,
        default=ROOT / "config" / "firestore_seed.json",
    )
    parser.add_argument("--project-id")
    parser.add_argument("--emulator", metavar="HOST:PORT")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument(
        "--allow-production-seed",
        action="store_true",
        help="Allow synthetic data to be written outside the emulator.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if args.project_id:
        os.environ["FIREBASE_PROJECT_ID"] = args.project_id
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project_id)
    if args.emulator:
        os.environ["FIRESTORE_EMULATOR_HOST"] = args.emulator

    using_emulator = bool(os.getenv("FIRESTORE_EMULATOR_HOST"))
    if not args.verify_only:
        if not using_emulator and not args.allow_production_seed:
            raise SystemExit(
                "Refusing to write synthetic data to production. Use the emulator "
                "or explicitly pass --allow-production-seed for staging."
            )
        counts = write_collections(load_seed(args.seed))
        print("Seed completed:")
        for collection_name, count in counts.items():
            print(f"- {collection_name}: {count} document(s)")

    verify_collections()


if __name__ == "__main__":
    main()
