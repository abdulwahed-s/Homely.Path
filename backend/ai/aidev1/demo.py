"""End-to-end demo for the AI Developer 1 pipeline (RealDoor).

Runs the Document Evidence Agent over the organizer's synthetic PDFs and the
Profile Reconciliation Agent over each household, then prints structured
evidence, confidence, source boxes, security flags, and conflicts.

Modes
-----
- offline (default): a gold-backed fake vision model answers classification and
  extraction, so the *real* pipeline (PDF loading, box location, normalization,
  confidence, injection scan, reconciliation) runs deterministically and free.
- online (``--online``): uses the real OpenAI vision model. Requires
  ``OPENAI_API_KEY`` (and optionally ``REALDOOR_VISION_MODEL``).

Usage
-----
    python demo.py                 # all households, offline
    python demo.py --household HH-002
    python demo.py --online        # real model
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.document_evidence.agent import DocumentEvidenceAgent  # noqa: E402
from backend.ai.document_evidence.env_config import find_organizer_pack, load_env  # noqa: E402
from backend.ai.document_evidence.ocr import build_ocr_engine  # noqa: E402
from backend.ai.document_evidence.tests.fakes.gold_llm import GoldBackedLLM  # noqa: E402
from backend.ai.profile_reconciliation.agent import ReconciliationAgent  # noqa: E402

load_env()

_PACK = find_organizer_pack()
if _PACK is None:
    raise SystemExit(
        "organizer_pack not found. Set REALDOOR_ORGANIZER_PACK or place it at the project root."
    )
DOCS_DIR = _PACK / "synthetic_documents" / "documents"
GOLD_PATH = _PACK / "synthetic_documents" / "gold" / "document_gold.jsonl"


def load_gold_index():
    index = {}
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                record = json.loads(line)
                index[record["document_id"]] = record
    return index


def build_online_llm():
    from backend.ai.document_evidence.factory import build_vision_llm

    return build_vision_llm()


def print_document(response):
    doc = response.document
    print(f"  Document {doc.document_id}  [{doc.document_type.value}]")
    if doc.security_flags:
        print(f"    security_flags: {[f.value for f in doc.security_flags]}")
    for field in doc.fields:
        box = field.source
        coords = f"[{box.x1:.0f},{box.y1:.0f},{box.x2:.0f},{box.y2:.0f}] p{box.page}"
        manual = " (manual)" if field.requires_manual_entry else ""
        print(
            f"    - {field.field_name:>18}: {str(field.normalized_value):<28} "
            f"conf={field.confidence:.2f}/{field.confidence_level.value:<6} "
            f"{coords}{manual}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="RealDoor AI Dev 1 pipeline demo")
    parser.add_argument("--online", action="store_true", help="use the real OpenAI model")
    parser.add_argument("--household", help="limit to one household id, e.g. HH-002")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--no-ocr", action="store_true", help="disable OCR for rasterized pages")
    args = parser.parse_args()

    gold_index = load_gold_index()
    ocr_engine = None if args.no_ocr else build_ocr_engine()
    # Build the real model client once (online); offline uses a per-document fake.
    online_llm = build_online_llm() if args.online else None

    households = defaultdict(list)
    for document_id, record in gold_index.items():
        households[record["household_id"]].append(document_id)
    for ids in households.values():
        ids.sort()

    target = sorted(households) if not args.household else [args.household]
    json_out = {}

    for household_id in target:
        doc_ids = households.get(household_id, [])
        if not doc_ids:
            print(f"Unknown household: {household_id}", file=sys.stderr)
            continue

        print(f"\n=== Household {household_id} ===")
        results = []
        for document_id in doc_ids:
            record = gold_index[document_id]
            pdf_path = DOCS_DIR / record["file_name"]
            llm = online_llm if args.online else GoldBackedLLM(record)
            agent = DocumentEvidenceAgent(llm, ocr_engine=ocr_engine)
            response = agent.process_document(
                pdf_path, document_id, session_id=f"demo-{household_id}"
            )
            results.append(response.document)
            if not args.json:
                print_document(response)

        recon = ReconciliationAgent().reconcile(results)
        if not args.json:
            if recon.conflicts:
                print(f"  Conflicts ({len(recon.conflicts)}):")
                for conflict in recon.conflicts:
                    print(f"    ! {conflict.code} [{conflict.severity.value}] "
                          f"docs={conflict.document_ids}")
                    print(f"        {conflict.message}")
            else:
                print("  Conflicts: none")

        if args.json:
            json_out[household_id] = {
                "documents": [json.loads(d.model_dump_json()) for d in results],
                "conflicts": [
                    {
                        "code": c.code,
                        "severity": c.severity.value,
                        "document_ids": c.document_ids,
                        "message": c.message,
                        "observed_values": c.observed_values,
                    }
                    for c in recon.conflicts
                ],
            }

    if args.json:
        print(json.dumps(json_out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
