"""Drive the FULL AI workflow against a LIVE uvicorn server over real TCP.

Stands in for the future website: a plain HTTP client (httpx) calling the
deployed routes. Usage:

    python backend/verify_live_http.py http://127.0.0.1:8011

Runs HH-002 (conflict + injection case) through:
    extract (x4 docs) -> reconcile -> [FS calc] -> ask -> readiness -> safety-check
and prints the actual server output at every step. Works against a gold-mode or
a real-OpenAI-mode server; /health reports which. The AI endpoints run real
logic in both modes -- in gold mode only the vision model's *reading* of the
page is substituted; in openai mode even that is live.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.calculations.service import calculate_household
from backend.integration.document_summary_builder import build_document_summaries
from backend.integration.evaluation_request_builder import build_evaluation_request
from tests.integration.adapters import build_test_confirmed_profile

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
HH = sys.argv[2] if len(sys.argv) > 2 else "HH-002"
PACK = ROOT / "organizer_pack"
DOCS = PACK / "synthetic_documents" / "documents"
GOLD = {
    json.loads(l)["document_id"]: json.loads(l)
    for l in (PACK / "synthetic_documents" / "gold" / "document_gold.jsonl").read_text(encoding="utf-8").splitlines()
    if l.strip()
}
CALC_CTX_KEYS = ["household_id", "household_size", "annualized_income", "threshold",
                 "comparison", "formula_steps", "calculation_source", "rule_year", "citations"]


def hh_docs(hh: str) -> list[str]:
    return sorted(d for d, r in GOLD.items() if r["household_id"] == hh)


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180)
    health = client.get("/health").json()
    print(f"HEALTH: {health}")
    mode = health.get("mode")

    print(f"\n===== STEP 1: EXTRACT ({HH}) — live vision path: {'REAL OpenAI' if mode == 'openai' else 'gold-backed'} =====")
    extracted = []
    for doc_id in hh_docs(HH):
        rec = GOLD[doc_id]
        with (DOCS / rec["file_name"]).open("rb") as fh:
            resp = client.post(
                "/internal/ai/extract",
                data={"document_id": doc_id, "session_id": "LIVE"},
                files={"file": (rec["file_name"], fh, "application/pdf")},
            )
        print(f"\n  [{doc_id}] HTTP {resp.status_code}")
        if resp.status_code != 200:
            print(f"    body: {resp.text}")
            print("\n  >>> REAL MODE COULD NOT PRODUCE OUTPUT (see error above). Aborting real run.")
            return 2
        doc = resp.json()["document"]
        doc["household_id"], doc["file_name"], doc["synthetic"] = rec["household_id"], rec["file_name"], True
        extracted.append(doc)
        print(f"    type={doc['document_type']}  security_flags={doc['security_flags']}")
        for f in doc["fields"]:
            print(f"      {f['field_name']:>18}: value={str(f['value']):<26} conf={f['confidence']} "
                  f"{f['confidence_level']:<6} manual={f['requires_manual_entry']}")

    print("\n===== STEP 3: RECONCILE =====")
    recon = client.post("/internal/ai/reconcile", json={"documents": extracted})
    print(f"  HTTP {recon.status_code}")
    reconciliation = recon.json()
    for c in reconciliation["conflicts"]:
        print(f"    CONFLICT {c['code']} [{c['severity']}] docs={c['document_ids']}: {c['message']}")
    if not reconciliation["conflicts"]:
        print("    (no conflicts)")

    print("\n===== STEP 5: CALCULATE (FS deterministic + simulated renter confirmation; NOT an AI call) =====")
    confirmed = build_test_confirmed_profile(household_id=HH, documents=extracted)
    calc = calculate_household(confirmed)
    print(f"  status={calc['calculation_status']}  annualized_income={calc['annualized_income']}  "
          f"threshold={calc['threshold']}  comparison={calc['comparison']}")
    print(f"  formula_steps={calc['formula_steps']}")

    print("\n===== STEP 6: ASK (citation + effective date for the threshold; folded into /ask) =====")
    ask = client.post("/internal/ai/ask", json={
        "request": {"session_id": "LIVE", "household_id": HH,
                    "question": "What is the frozen 60% income threshold for this household size?"},
        "context": {"session_id": "LIVE", "active_household_id": HH,
                    "calculation": {k: calc[k] for k in CALC_CTX_KEYS if k in calc}},
    })
    print(f"  HTTP {ask.status_code}")
    answer = ask.json()["answer"]
    print(f"  status={answer['status']}")
    print(f"  answer={answer['answer']}")
    print(f"  citations={[(c.get('rule_id'), c.get('effective_date')) for c in answer['citations']]}")

    print("\n===== STEP 8: READINESS =====")
    summaries = build_document_summaries(extracted)
    gaps = ["GIG_INCOME_UNCORROBORATED"] if any(d["document_type"] == "gig_statement" for d in extracted) else []
    req = build_evaluation_request(
        household_id=HH, session_id="LIVE", extracted_documents=extracted,
        reconciliation=reconciliation, confirmed_profile=confirmed, calculation=calc,
        document_summaries=summaries, upstream_evidence_gaps=gaps,
    )
    ready = client.post("/internal/ai/readiness", json=req)
    print(f"  HTTP {ready.status_code}")
    rb = ready.json()
    sub = rb.get("organizer_submission")
    print(f"  readiness_status={rb['readiness_status']}")
    print(f"  review_reasons={[r['code'] for r in (sub or {}).get('review_reasons', [])]}")
    print(f"  organizer_submission.annualized_income={(sub or {}).get('annualized_income')}  "
          f"comparison={(sub or {}).get('comparison')}")

    print("\n===== STEP 9: SAFETY-CHECK (standalone gate) =====")
    safety = client.post("/internal/ai/safety-check", json={
        "request_text": "",
        "response_text": rb["readiness_status"],
        "citations": (sub or {}).get("citations", []),
        "active_household_id": HH,
        "referenced_household_ids": [HH],
        "calculation_source": "deterministic",
        "readiness_status": rb["readiness_status"],
        "unconfirmed_values_labelled": True,
    })
    print(f"  HTTP {safety.status_code}  {safety.json()}")

    print(f"\nMODE={mode}. extract/reconcile/ask/readiness/safety all returned live server output over TCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
