# AI Developer 1 — Integration Guide

**Scope owned:** "user uploads a document" → "structured profile evidence for confirmation."
Two agents, exposed as two HTTP endpoints. Everything downstream (confirm/edit
UI, rules, calculations, readiness, packet, safety gate) is **not** ours.

- **Document Evidence Agent** → `POST /internal/ai/extract`
- **Profile Reconciliation Agent** → `POST /internal/ai/reconcile`

The wire types are defined by the **frozen contract**
`contracts/extraction_contract.py` (owned by Integration; imported by AI Dev 1
and AI Dev 2). The extract response is that contract verbatim.

---

## 0. Running the service

```bash
pip install -r requirements.txt          # fastapi, uvicorn, python-multipart, pydantic, PyMuPDF, openai, Pillow, rapidocr-onnxruntime
python serve.py                          # http://127.0.0.1:8000
python serve.py --host 0.0.0.0 --port 9000
```

Requires `OPENAI_API_KEY` (+ optional `REALDOOR_VISION_MODEL`, default `gpt-4o-mini`)
in `aidev1/.env`. OCR for image-only PDFs is automatic.

- Interactive schema / try-it: **`GET /docs`** (Swagger UI, auto-generated)
- Machine-readable schema: **`GET /openapi.json`**
- Liveness: **`GET /health`** → `{"status":"ok"}`

### Deploy note — confidence calibration (REQUIRED for FR1.13)

`calibration_data.json` is **gitignored** (gold-derived), so a fresh clone/deploy
has no calibration and runs **uncalibrated** (identity passthrough). `serve.py`
logs a `WARNING` at startup when this happens, but to actually satisfy FR1.13 the
deploy must fit it. The `organizer_pack` is **not** in the repo, so it must be
present in the build environment for the fit step.

Recommended **Render build command** (fit, then drop the draft pack so it never
ships in the running image):

```bash
pip install -r requirements.txt && python calibrate.py --offline && rm -rf organizer_pack
```

- `calibrate.py --offline` uses gold + OCR only (no OpenAI key needed) and writes `calibration_data.json`.
- The **runtime** service (`serve.py`) does **not** need `organizer_pack` — only `calibration_data.json` (build artifact) + `OPENAI_API_KEY`.
- If you'd rather keep the pack off Render entirely, run `python calibrate.py --offline` locally and ship only the resulting `calibration_data.json` as a build secret/artifact.

---

## 1. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/internal/ai/extract` | Classify one uploaded PDF and extract allowlisted fields with source boxes, confidence, and security flags. One call per document. |
| `POST` | `/internal/ai/reconcile` | Compare already-extracted documents for a household and return cross-document conflict objects. One call per household (after ≥1 extract). |
| `GET`  | `/health` | Liveness probe. |

---

## 2. `POST /internal/ai/extract`

### Request — `multipart/form-data`

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `file` | file (PDF) | yes | The uploaded document bytes. PDF only. |
| `document_id` | string (form field) | yes | Your stable id for this document (echoed back). |
| `session_id` | string (form field) | yes | Anonymous session token; echoed into the response. |

```bash
curl -X POST http://127.0.0.1:8000/internal/ai/extract \
  -F "document_id=HH-001-D02" \
  -F "session_id=sess_abc123" \
  -F "file=@paystub.pdf;type=application/pdf"
```

### Response `200` — `ExtractionResponse` (frozen contract)

```jsonc
{
  "session_id": "sess_abc123",
  "document": {
    "document_id": "HH-001-D02",
    "document_type": "pay_stub",              // enum: application_summary | pay_stub | employment_letter | benefit_letter | gig_statement | unknown
    "security_flags": [],                     // see §5 enum
    "fields": [
      {
        "field_name": "gross_pay",
        "value": "$1,395.00",                 // display string exactly as read (may be null)
        "normalized_value": 1395.0,            // typed value for downstream math (float|int|string|null)
        "confidence": 0.86,                    // calibrated [0..1]
        "confidence_level": "high",            // high >=0.80 | medium >=0.50 | low <0.50
        "confirmation_status": "awaiting_confirmation",
        "requires_manual_entry": false,        // true => don't prefill; renter must type it
        "source": {
          "page": 1,                           // 1-based
          "x1": 412.5, "y1": 628.0,            // PDF points, BOTTOM-LEFT origin
          "x2": 486.0, "y2": 640.0,
          "source_description": "'gross pay' on page 1 of the pay stub document"
        }
      }
    ]
  },
  "activity_events": [
    {"timestamp":"2026-07-19T02:00:00+00:00","agent":"document_evidence_agent","action":"load_document","status":"PASS","metadata":{"pages":1,"rasterized":false}},
    {"timestamp":"2026-07-19T02:00:00+00:00","agent":"document_evidence_agent","action":"scan_injection","status":"PASS","metadata":{"flagged":false,"matches":[]}},
    {"timestamp":"2026-07-19T02:00:01+00:00","agent":"document_evidence_agent","action":"classify_document","status":"PASS","metadata":{"document_type":"pay_stub","confidence":0.97}},
    {"timestamp":"2026-07-19T02:00:03+00:00","agent":"document_evidence_agent","action":"extract_fields","status":"PASS","metadata":{"field_count":9,"manual_entry":0}}
  ]
}
```

> **Coordinate system:** boxes are `pdf_points_bottom_left_origin`
> (`0 <= x1 < x2 <= page_width`, `0 <= y1 < y2 <= page_height`, page size normally 612×792).
> If the browser renders with a top-left origin, flip Y: `y_top = page_height - y2`.

### Field semantics you must honor

- **`requires_manual_entry: true`** → do **not** prefill; render an empty input and ask the renter to type the value (FR1.6 / FR1.13-low). This is set when a value has no valid source box, failed to normalize, **or is `confidence_level: "low"`**.
- **`confidence_level`**: `high` → prefilled, still require confirm; `medium` → prefilled, surface "needs careful review"; **`low` → `value` and `normalized_value` are returned as `null`** (never guessed) and `requires_manual_entry` is `true`.
- **`source.source_description`** is the accessible, plain-language location text (FR6.4). Use it as alt-text/aria description for the highlight.
- Fields the model could not read are **omitted** from `fields` (never guessed).

---

## 3. `POST /internal/ai/reconcile`

### Request — `application/json`

Send back the **`document` objects** you received from `extract` (the frozen
`DocumentExtractionResult` shape) for one household:

```jsonc
{
  "documents": [
    {
      "document_id": "HH-002-D02",
      "document_type": "pay_stub",
      "security_flags": [],
      "fields": [
        {"field_name":"regular_hours","value":"40","normalized_value":40,"confidence":0.9,"confidence_level":"high","confirmation_status":"awaiting_confirmation","requires_manual_entry":false,"source":{"page":1,"x1":100,"y1":700,"x2":140,"y2":712,"source_description":"'regular hours' on page 1 of the pay stub document"}},
        {"field_name":"hourly_rate","value":"$24.00","normalized_value":24.0,"confidence":0.9,"confidence_level":"high","confirmation_status":"awaiting_confirmation","requires_manual_entry":false,"source":{"page":1,"x1":100,"y1":680,"x2":140,"y2":692,"source_description":"'hourly rate' on page 1 of the pay stub document"}},
        {"field_name":"gross_pay","value":"$1,395.00","normalized_value":1395.0,"confidence":0.9,"confidence_level":"high","confirmation_status":"awaiting_confirmation","requires_manual_entry":false,"source":{"page":1,"x1":100,"y1":660,"x2":160,"y2":672,"source_description":"'gross pay' on page 1 of the pay stub document"}}
      ]
    }
  ]
}
```

### Response `200`

```jsonc
{
  "conflicts": [
    {
      "conflict_id": "HH-002-D02:PAY_STUB_TOTAL_CONFLICT",
      "code": "PAY_STUB_TOTAL_CONFLICT",          // see enum below
      "severity": "blocking_for_confirmation",     // info | warning | blocking_for_confirmation
      "message": "Pay stub gross pay (1395.0) does not match regular_hours x hourly_rate (40.0 x 24.0 = 960.0). Human confirmation required.",
      "document_ids": ["HH-002-D02"],
      "field_names": ["regular_hours","hourly_rate","gross_pay"],
      "observed_values": {
        "regular_hours": 40.0, "hourly_rate": 24.0, "gross_pay": 1395.0, "expected_gross": 960.0
      },
      "source_refs": [ /* SourceBox objects for the involved fields */ ]
    }
  ],
  "activity_events": [
    {"timestamp":"2026-07-19T02:00:05+00:00","agent":"profile_reconciliation_agent","action":"reconcile_documents","status":"ACTION_REQUIRED","metadata":{"document_count":2,"conflict_count":1,"conflict_codes":["PAY_STUB_TOTAL_CONFLICT"]}}
  ]
}
```

**Conflict codes**

| `code` | Meaning | Default severity |
|--------|---------|------------------|
| `PAY_STUB_TOTAL_CONFLICT` | Single stub: `regular_hours × hourly_rate ≠ gross_pay` | `blocking_for_confirmation` |
| `PAY_FREQUENCY_CONFLICT` | Pay stubs disagree on `pay_frequency` | `blocking_for_confirmation` |
| `OVERLAPPING_PAY_PERIODS` | Two stubs cover the identical pay period (duplicate) | `warning` |
| `PERSON_NAME_CONFLICT` | Documents show different applicant names | `warning` |

> **Not a conflict:** differing `gross_pay` across *different* pay periods is
> legitimate variance (e.g. overtime) and is intentionally **not** flagged.
> Genuine duplicate evidence is caught by `OVERLAPPING_PAY_PERIODS`; intra-stub
> arithmetic mismatches by `PAY_STUB_TOTAL_CONFLICT`.

**`observed_values` shape.** *Cross-document* conflicts (`PAY_FREQUENCY_CONFLICT`,
`OVERLAPPING_PAY_PERIODS`, `PERSON_NAME_CONFLICT`) use a uniform per-document map
so you can render side-by-side directly:

```jsonc
"observed_values": {
  "field": "pay_frequency",             // string, or array of field names for overlaps
  "per_document": { "HH-002-D02": "weekly", "HH-002-D03": "biweekly" }
}
```

`source_refs` is ordered to match `per_document` insertion order (document
order). The single-document `PAY_STUB_TOTAL_CONFLICT` instead reports its
arithmetic inputs (`regular_hours`, `hourly_rate`, `gross_pay`, `expected_gross`)
since it compares fields *within* one stub. You never decide which value is
correct; render both and let the renter resolve.

---

## 4. Error responses

| Situation | Status | Body | Notes |
|-----------|--------|------|-------|
| Missing `file` / `document_id` / `session_id` | `422` | `{"detail":[{"loc":...,"msg":...}]}` | FastAPI validation (automatic). |
| `reconcile` body doesn't match schema | `422` | `{"detail":[...]}` | e.g. a field missing `source`. |
| **Corrupted / non-PDF file** | `400` | `{"error_code":"INVALID_DOCUMENT","detail":"could not open source as PDF: ..."}` | Graceful; no 500. |
| **Empty upload (0 bytes)** | `400` | `{"error_code":"INVALID_DOCUMENT","detail":"uploaded file is empty"}` | Graceful. |
| Unsupported / unrecognized document | `200` | normal `ExtractionResponse` with `document_type:"unknown"` and `security_flags:["unsupported_document"]`, usually empty `fields` | Not an error — handle by prompting re-upload. |
| Image-only PDF where OCR found nothing | `200` | `security_flags` includes `"ocr_failure"`, fields may be empty/low-confidence | Show manual-entry path. |
| Prompt injection detected | `200` | `security_flags` includes `"prompt_injection_detected"`; the embedded instruction is **never** returned as a field | Render the "🛑 instruction ignored" banner (FR1.8). |

---

## 5. Enum reference

- **`document_type`**: `application_summary`, `pay_stub`, `employment_letter`, `benefit_letter`, `gig_statement`, `unknown`
- **`confidence_level`**: `high` (≥0.80), `medium` (≥0.50), `low` (<0.50)
- **`confirmation_status`**: `awaiting_confirmation`, `confirmed`, `user_edited`, `rejected` — we always emit `awaiting_confirmation`; the other values are for **your** confirm/edit workflow.
- **`security_flags[]`**: `prompt_injection_detected`, `adversarial_content`, `unsupported_document`, `ocr_failure`
- **`activity_events[].status`**: `PASS`, `ACTION_REQUIRED`, `WAITING`

### Allowlisted fields per document type (nothing else is extracted)

| document_type | fields |
|---------------|--------|
| `application_summary` | `person_name`, `household_size`, `address`, `application_date` |
| `pay_stub` | `person_name`, `pay_date`, `pay_period_start`, `pay_period_end`, `pay_frequency`, `regular_hours`, `hourly_rate`, `gross_pay`, `net_pay` |
| `employment_letter` | `person_name`, `document_date`, `weekly_hours`, `hourly_rate` |
| `benefit_letter` | `person_name`, `document_date`, `monthly_benefit`, `benefit_frequency` |
| `gig_statement` | `person_name`, `statement_month`, `gross_receipts`, `platform_fees` |

Normalized types: money (`hourly_rate`/`gross_pay`/`net_pay`/`platform_fees`) → float;
`household_size` → int; `regular_hours`/`weekly_hours`/`monthly_benefit`/`gross_receipts` → int-if-integral else float;
dates → `YYYY-MM-DD`; `statement_month` → `YYYY-MM`; frequency → one of `weekly|biweekly|semimonthly|monthly|annual`.

---

## 6. Who does what

**Full-stack sends us:**
- `session_id` (anonymous token), `document_id`, and the PDF `file` on `extract`.
- The collected `document` objects on `reconcile` (one household at a time).

**Full-stack gets back and is responsible for:**
- Rendering the **bounding boxes** (`source.x1..y2`, bottom-left origin) over the page image, with `source_description` as accessible text (FR1.5, FR6.4).
- The **confirm/edit workflow** (FR1.9): nothing is "confirmed" until the renter acts. Set `confirmation_status` on your side; hold confirmed values.
- Honoring `requires_manual_entry` / `confidence_level` (don't prefill low-confidence values) (FR1.6, FR1.13).
- Rendering the **security banner** when `security_flags` is non-empty (FR1.8).
- Rendering the **side-by-side conflict UI** from `conflicts[]` with both `source_refs`, and blocking downstream calc until resolved → `NEEDS_REVIEW` (FR1.12). We only *surface* conflicts.
- Streaming **`activity_events[]`** into the live ticker / replay (FR4.7).
- **Holding confirmed values** and calling **AI Developer 2's** endpoints (rules, calc, readiness) — we do not call downstream.

**AI Developer 2 / Integration:**
- Owns and freezes `contracts/extraction_contract.py`. If it changes, both `extract` output and `reconcile` input change with it.
- The reconciliation conflict object is **AI-Dev-1-local** (not yet a frozen contract). Coordinate before depending on `observed_values` key names.

---

## 7. Implemented vs. not implemented (integrate-today status)

### ✅ Implemented & callable today
- `POST /internal/ai/extract` — classify + allowlisted extract + boxes + confidence + injection flags + activity events, for all **5** document types. Text and image-only (OCR) PDFs.
- `POST /internal/ai/reconcile` — 5 conflict detectors (gross-total, pay-frequency, gross-pay, duplicate periods, person-name).
- Calibrated confidence (`confidence` is gold-fitted), `confidence_level` tiers, and enforced low-confidence behavior (low → `null` value + `requires_manual_entry`).
- Injection scan over text **and OCR-recovered text** (image-only pages included).
- Structured `400 INVALID_DOCUMENT` on corrupt/empty uploads.
- Uniform per-document `observed_values` on cross-document conflicts.
- `security_flags`, `activity_events`, accessible `source_description`.
- `GET /health`, `GET /docs`, `GET /openapi.json`.

### 🟡 Implemented with a caveat
- **`source_description`** is field/type/page-based (e.g. "'gross pay' on page 1 of the pay stub document"), not layout-region-aware ("earnings table, row labelled…"). Meets FR6.4; less rich than the example.
- **`adversarial_content`** security flag is defined in the contract but not currently emitted (only `prompt_injection_detected`, `unsupported_document`, `ocr_failure` are).
- **`calibration_data.json`** is gitignored (gold-derived). On a fresh checkout, run `python calibrate.py` or confidence falls back to identity (uncalibrated) — still functional, just not calibrated.

### ❌ Not implemented (by design / out of scope)
- **Employer-name** and **current-vs-YTD** conflict detection — those fields are **not in the allowlist**, so they are intentionally not extracted or compared.
- Confirm/edit workflow, downstream rules/calc/readiness/packet/safety — **not ours** (full-stack + AI Dev 2).
- Auth on the endpoints (internal service; assumed behind the app's session layer).

---

*Contract source of truth: `contracts/extraction_contract.py`. This doc describes the live behavior of `backend/ai/api.py`, `backend/ai/document_evidence/`, and `backend/ai/profile_reconciliation/`.*
