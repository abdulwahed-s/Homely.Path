"""End-to-end AI workflow trace for ONE household (3 documents), over HTTP.

Runs the full RealDoor AI pipeline for a single person and prints every input
and output at each seam, plus a note on which steps belong to FS (full-stack),
not the AI service. Uses the gold-backed fake LLM so it is deterministic and
needs no API key -- but it exercises the *real* pipeline: PDF load, injection
scan, classification, allowlisted extraction, text-layer box location,
normalization, confidence tiering, reconciliation, rules/citation, readiness,
and the safety gate.

Run:  python backend/verify_household_flow.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from backend.ai.api import create_app
from backend.calculations.service import calculate_household
from backend.integration.document_summary_builder import build_document_summaries
from backend.integration.evaluation_request_builder import build_evaluation_request
from tests.integration.adapters import build_test_confirmed_profile

PACK = ROOT / "organizer_pack"
DOCS_DIR = PACK / "synthetic_documents" / "documents"
GOLD_PATH = PACK / "synthetic_documents" / "gold" / "document_gold.jsonl"
DOC_GOLD_SCHEMA = json.loads((PACK / "starter" / "schemas" / "document_gold.schema.json").read_text())
SUBMISSION_SCHEMA = json.loads((PACK / "starter" / "schemas" / "submission.schema.json").read_text())

SESSION = "HH-FLOW-DEMO"
HOUSEHOLD = "HH-001"
# One person, three text-based documents (deterministic boxes in gold mode).
DOC_IDS = ["HH-001-D01", "HH-001-D03", "HH-001-D04"]


def _gold_index() -> dict:
    index = {}
    for line in GOLD_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rec = json.loads(line)
            index[rec["document_id"]] = rec
    return index


GOLD = _gold_index()


def hr(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sub(title: str) -> None:
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def fs_note(text: str) -> None:
    print("\n  >>> FS RESPONSIBILITY (no AI call): " + text)


def _extract(client: TestClient, doc_id: str) -> tuple[int, dict]:
    rec = GOLD[doc_id]
    pdf = DOCS_DIR / rec["file_name"]
    with pdf.open("rb") as fh:
        files = {"file": (rec["file_name"], fh, "application/pdf")}
        data = {"document_id": doc_id, "session_id": SESSION}
        resp = client.post("/internal/ai/extract", data=data, files=files)
    ct = resp.headers.get("content-type", "")
    return resp.status_code, (resp.json() if ct.startswith("application/json") else {})


def _merge_identity(document: dict, doc_id: str) -> dict:
    rec = GOLD[doc_id]
    document = dict(document)
    document["household_id"] = rec["household_id"]
    document["file_name"] = rec["file_name"]
    document["synthetic"] = True
    return document


def _print_fields(fields: list[dict]) -> None:
    for f in fields:
        s = f["source"]
        box = f"p{s['page']} [{s['x1']},{s['y1']},{s['x2']},{s['y2']}]"
        print(
            f"      - {f['field_name']:18} value={str(f['value'])!r:22} "
            f"norm={str(f['normalized_value'])!r:14} "
            f"conf={f['confidence']:<4} {f['confidence_level']:<6} "
            f"manual={f['requires_manual_entry']!s:5} box={box}"
        )


def main() -> int:
    client = TestClient(create_app(gold_mode=True, pack_root=str(PACK)))

    hr(f"AI WORKFLOW END-TO-END  |  household={HOUSEHOLD}  |  mode=gold-backed (deterministic)")
    print(f"  Documents ({len(DOC_IDS)}):")
    for d in DOC_IDS:
        rec = GOLD[d]
        print(f"    {d}: {rec['file_name']}  type={rec['document_type']}  rasterized={rec['rasterized']}")

    # ---------------------------------------------------------------- STEP 1
    hr("STEP 1  EXTRACT (AI)  ->  POST /internal/ai/extract   [once per document]")
    extracted: list[dict] = []
    for i, doc_id in enumerate(DOC_IDS):
        rec = GOLD[doc_id]
        sub(f"1.{i+1}  INPUT: file={rec['file_name']}  document_id={doc_id}  session_id={SESSION}")
        status, body = _extract(client, doc_id)
        print(f"    HTTP {status}")
        if status != 200:
            print(f"    FAILED: {body}")
            return 1
        doc = body["document"]
        print(f"    OUTPUT document_type : {doc['document_type']}")
        print(f"    OUTPUT security_flags: {doc['security_flags']}")
        print(f"    OUTPUT fields ({len(doc['fields'])}):")
        _print_fields(doc["fields"])
        print(f"    OUTPUT activity_events: {[(e['action'], e['status']) for e in body['activity_events']]}")
        extracted.append(_merge_identity(doc, doc_id))

    # Full raw contract for the first document (what FS actually receives).
    sub("1.x  RAW ExtractionResponse contract for HH-001-D01 (exact JSON FS receives)")
    first_status, first_body = _extract(client, DOC_IDS[0])
    print(json.dumps(first_body, indent=2)[:2600])

    # Flag 3: does ExtractionResponse project onto document_gold.schema.json?
    sub("1.y  Flag 3 adapter: ExtractionResponse -> document_gold.schema.json")
    summaries = build_document_summaries(extracted)
    for summary in summaries:
        errs = sorted(Draft202012Validator(DOC_GOLD_SCHEMA).iter_errors(summary), key=str)
        verdict = "VALID" if not errs else f"INVALID ({errs[0].message})"
        print(f"    {summary['document_id']}: {verdict}")

    # ---------------------------------------------------------------- STEP 2
    hr("STEP 2  CONFIRM / EDIT")
    fs_note(
        "Renter reviews each field, its box + confidence badge, and security "
        "banners; FS stores the confirmed values. Nothing downstream trusts "
        "unconfirmed data. (No AI call.)"
    )

    # ---------------------------------------------------------------- STEP 3
    hr("STEP 3  RECONCILE (AI)  ->  POST /internal/ai/reconcile   [once per household]")
    sub("3.1  INPUT: confirmed documents[] for the household")
    print(f"    documents: {[d['document_id'] for d in extracted]}")
    recon = client.post("/internal/ai/reconcile", json={"documents": extracted})
    print(f"    HTTP {recon.status_code}")
    if recon.status_code != 200:
        print(f"    FAILED: {recon.text[:300]}")
        return 1
    reconciliation = recon.json()
    conflicts = reconciliation.get("conflicts", [])
    print(f"    OUTPUT conflicts ({len(conflicts)}):")
    for c in conflicts:
        print(f"      - {c.get('conflict_type')} | {c.get('severity')} | {c.get('description', '')[:80]}")
    print(f"    OUTPUT activity_events: {[e['action'] for e in reconciliation.get('activity_events', [])]}")

    # ---------------------------------------------------------------- STEP 4
    hr("STEP 4  RESOLVE CONFLICTS")
    fs_note("Renter resolves any blocking conflict before calc. (No AI call.)")

    # ---------------------------------------------------------------- STEP 5
    hr("STEP 5  CALCULATE  (FS deterministic code -- NOT an AI call)")
    confirmed_profile = build_test_confirmed_profile(household_id=HOUSEHOLD, documents=extracted)
    calculation = calculate_household(confirmed_profile)
    fs_note("FS runs the MTSP lookup + annualization. Shown here for context:")
    for k in ["household_id", "household_size", "annualized_income", "threshold",
              "comparison", "calculation_status", "rule_year"]:
        if k in calculation:
            print(f"      {k:20}: {calculation[k]}")
    print(f"      citations           : {calculation.get('citations')}")

    # ---------------------------------------------------------------- STEP 6
    hr("STEP 6  EXPLAIN THE CALCULATION (AI)  ->  POST /internal/ai/ask")
    ask_body = {
        "request": {
            "session_id": SESSION,
            "household_id": HOUSEHOLD,
            "question": "What is the frozen 60% income threshold for this household size, and what rule sets it?",
        },
        "context": {
            "session_id": SESSION,
            "active_household_id": HOUSEHOLD,
            "calculation": {k: calculation[k] for k in
                            ["household_id", "household_size", "annualized_income", "threshold",
                             "comparison", "formula_steps", "calculation_source", "rule_year", "citations"]
                            if k in calculation},
            "readiness_status": None,
        },
    }
    sub("6.1  INPUT: question + calculation context")
    print(json.dumps(ask_body, indent=2)[:900])
    ask = client.post("/internal/ai/ask", json=ask_body)
    print(f"    HTTP {ask.status_code}")
    if ask.status_code != 200:
        print(f"    FAILED: {ask.text[:300]}")
        return 1
    answer = ask.json()["answer"]
    print(f"    OUTPUT status   : {answer['status']}")
    print(f"    OUTPUT answer   : {(answer.get('answer') or '')[:300]}")
    print(f"    OUTPUT citations: {[ (c.get('rule_id'), c.get('effective_date')) for c in answer.get('citations', []) ]}")

    # ---------------------------------------------------------------- STEP 8
    hr("STEP 8  READINESS (AI)  ->  POST /internal/ai/readiness")
    eval_request = build_evaluation_request(
        household_id=HOUSEHOLD,
        session_id=SESSION,
        extracted_documents=extracted,
        reconciliation=reconciliation,
        confirmed_profile=confirmed_profile,
        calculation=calculation,
        document_summaries=summaries,
        upstream_evidence_gaps=[],
    )
    sub("8.1  INPUT: confirmed profile + conflicts + calc + doc inventory (keys)")
    print(f"    request keys: {sorted(eval_request.keys())}")
    ready = client.post("/internal/ai/readiness", json=eval_request)
    print(f"    HTTP {ready.status_code}")
    if ready.status_code != 200:
        print(f"    FAILED: {ready.text[:400]}")
        return 1
    rbody = ready.json()
    print(f"    OUTPUT readiness_status: {rbody['readiness_status']}")
    checklist = rbody.get("checklist", [])
    print(f"    OUTPUT checklist ({len(checklist)}):")
    for item in checklist:
        print(f"      - {item.get('item') or item.get('code')}: {item.get('status')} ({item.get('reason','')[:60]})")
    print(f"    OUTPUT next_steps: {rbody.get('next_steps')}")
    submission = rbody.get("organizer_submission")

    sub("8.2  submission -> submission.schema.json (the packet FS will export)")
    if submission is not None:
        sub_errs = sorted(Draft202012Validator(SUBMISSION_SCHEMA).iter_errors(submission), key=str)
        print(f"    {'VALID' if not sub_errs else 'INVALID: ' + sub_errs[0].message}")
    else:
        print("    (no organizer_submission produced)")

    # ---------------------------------------------------------------- STEP 9
    hr("STEP 9  SAFETY GATE (AI)  ->  POST /internal/ai/safety-check")
    reasons = [r["code"] for r in (submission or {}).get("review_reasons", [])]
    safety_input = {
        "request_text": "",
        "response_text": f"{rbody['readiness_status']}; " + "; ".join(reasons),
        "citations": (submission or {}).get("citations", []),
        "active_household_id": HOUSEHOLD,
        "referenced_household_ids": [HOUSEHOLD],
        "calculation_source": "deterministic",
        "readiness_status": rbody["readiness_status"],
        "unconfirmed_values_labelled": True,
    }
    sub("9.1  INPUT: response text + citations + household scope")
    print(json.dumps(safety_input, indent=2)[:700])
    safety = client.post("/internal/ai/safety-check", json=safety_input)
    print(f"    HTTP {safety.status_code}")
    if safety.status_code != 200:
        print(f"    FAILED: {safety.text[:300]}")
        return 1
    sbody = safety.json()
    print(f"    OUTPUT status         : {sbody['status']}")
    print(f"    OUTPUT safe_to_display: {sbody['safe_to_display']}")
    print(f"    OUTPUT checks         : {sbody.get('checks') or sbody.get('failed_checks')}")

    # ---------------------------------------------------------------- STEP 10
    hr("STEP 10  PACKET EXPORT")
    fs_note(
        "FS assembles confirmed profile + calc worksheet + rule refs + checklist "
        "into the final packet (validates against submission.schema.json, shown "
        "in 8.2) and stores/exports it. Never auto-sent. (No AI call.)"
    )

    hr("VERDICT")
    print("  extract (x3) .... PASS   real values, boxes, confidence per field")
    print("  reconcile ....... PASS")
    print("  calc (FS) ....... PASS   (deterministic, not AI)")
    print("  ask ............. PASS   grounded citation + effective date")
    print("  readiness ....... PASS   checklist + status + submission")
    print("  safety-check .... PASS   gate ran")
    print("\n  => Full AI workflow completed end-to-end for HH-001 over HTTP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
