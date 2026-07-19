"""Seed one synthetic structured chat session into the Firestore emulator."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.discovery.firebase_client import get_firestore_client


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        type=Path,
        default=ROOT / "config" / "chat_session_seed.json",
    )
    parser.add_argument("--project-id", default="homelypath")
    parser.add_argument(
        "--emulator-host",
        default=os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080"),
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    os.environ["FIRESTORE_EMULATOR_HOST"] = args.emulator_host
    os.environ["FIREBASE_PROJECT_ID"] = args.project_id
    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project_id

    payload = json.loads(args.seed.read_text(encoding="utf-8"))
    session_id = payload.get("session_id")
    household_id = payload.get("household_id")
    if not session_id or not household_id:
        raise ValueError("Seed requires session_id and household_id")

    db = get_firestore_client()
    reference = db.collection(
        os.getenv("CHAT_SESSION_COLLECTION", "chat_sessions")
    ).document(session_id)
    if not args.verify_only:
        reference.set(payload)

    snapshot = reference.get()
    if not snapshot.exists:
        raise RuntimeError(f"Chat session {session_id!r} was not found")
    stored = snapshot.to_dict() or {}
    if stored.get("household_id") != household_id:
        raise RuntimeError("Stored chat session household_id does not match")
    print(f"Verified synthetic chat session: {session_id}")


if __name__ == "__main__":
    main()
