"""Fit and persist confidence calibration against the organizer gold (FR1.13).

Runs the Document Evidence Agent over every gold document, evaluates each
extracted field against the gold value and bounding box, and fits a histogram
calibration model mapping raw confidence -> observed accuracy. The model is
saved to ``backend/ai/document_evidence/calibration_data.json`` and applied
automatically on subsequent runs.

Modes
-----
- online (default): real OpenAI model — the meaningful setting, since value
  accuracy only varies with a real model. Requires ``OPENAI_API_KEY``.
- ``--offline``: gold-backed fake — values are always correct, so only box
  accuracy varies; useful for wiring checks.

Usage
-----
    python calibrate.py            # online, all documents
    python calibrate.py --offline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.document_evidence import calibration  # noqa: E402
from backend.ai.document_evidence.agent import DocumentEvidenceAgent  # noqa: E402
from backend.ai.document_evidence.env_config import find_organizer_pack, load_env  # noqa: E402
from backend.ai.document_evidence.evaluation import (  # noqa: E402
    calibration_samples,
    evaluate_dataset,
    summarize,
)
from backend.ai.document_evidence.ocr import build_ocr_engine  # noqa: E402
from backend.ai.document_evidence.tests.fakes.gold_llm import GoldBackedLLM  # noqa: E402

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit confidence calibration vs gold")
    parser.add_argument("--offline", action="store_true", help="use the gold-backed fake model")
    parser.add_argument("--bins", type=int, default=10, help="number of calibration buckets")
    args = parser.parse_args()

    gold_index = load_gold_index()
    ocr_engine = build_ocr_engine()

    # Collect RAW scores: bypass any existing calibration during measurement.
    calibration.set_active(calibration.identity())

    if not args.offline:
        from backend.ai.document_evidence.factory import build_vision_llm

        shared_llm = build_vision_llm()

    results = []
    print(f"Running pipeline over {len(gold_index)} documents "
          f"({'offline gold fake' if args.offline else 'online OpenAI'})...")
    for document_id, record in sorted(gold_index.items()):
        pdf_path = DOCS_DIR / record["file_name"]
        llm = GoldBackedLLM(record) if args.offline else shared_llm
        agent = DocumentEvidenceAgent(llm, ocr_engine=ocr_engine)
        response = agent.process_document(pdf_path, document_id, session_id="calibrate")
        results.append(response.document)
        print(f"  {document_id}: {len(response.document.fields)} fields")

    evals = evaluate_dataset(results, gold_index)
    report = summarize(evals)

    samples = calibration_samples(evals)
    model = calibration.fit(samples, n_bins=args.bins)
    model.save()

    print("\n=== Evaluation vs gold ===")
    print(json.dumps(report, indent=2))
    print("\n=== Fitted calibration buckets (raw score range -> accuracy [n]) ===")
    width = 1.0 / model.n_bins
    for i in range(model.n_bins):
        acc = model.accuracy[i]
        acc_str = "  (no data)" if acc is None else f"{acc:.3f}"
        print(f"  [{i*width:.1f}-{(i+1)*width:.1f}) -> {acc_str}  [n={model.counts[i]}]")
    print(f"\nSaved calibration model to {calibration.DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
