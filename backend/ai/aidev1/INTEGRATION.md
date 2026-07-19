# RealDoor AI — Integration Guide

**One unified FastAPI service** exposes every AI-owned route. Full-stack (FS)
calls these over HTTP; the AI service holds **no session state**.

| Agent | Method | Path |
|-------|--------|------|
| Document Evidence | `POST` | `/internal/ai/extract` |
| Profile Reconciliation | `POST` | `/internal/ai/reconcile` |
| Rules & Chat (citations folded in) | `POST` | `/internal/ai/ask` |
| Readiness | `POST` | `/internal/ai/readiness` |
| Safety & Report | `POST` | `/internal/ai/safety-check` |
| Liveness | `GET` | `/health` |

Wire types for extract/reconcile come from the frozen contract
`contracts/extraction_contract.py`. Readiness output is validated against
`organizer_pack/starter/schemas/submission.schema.json`. Citation / effective-date
retrieval for the calc view is **folded into `/ask`** — there is no separate
citation endpoint.

---

## 0. Running the service

```bash
# from repo root
pip install -r requirements.txt
set PYTHONPATH=.                    # Windows PowerShell: $env:PYTHONPATH="."
python backend/serve.py             # real OpenAI mode → http://127.0.0.1:8000
python backend/serve.py --gold      # offline gold-backed extract (no API key)
python backend/serve.py --host 0.0.0.0 --port 9000
```

Requires `OPENAI_API_KEY` in `backend/ai/aidev1/.env` (or the process env) for
real extract. Optional: `REALDOOR_VISION_MODEL` (default `gpt-4o-mini`),
`REALDOOR_PACK_ROOT` or `REALDOOR_ORGANIZER_PACK` (aliases for the same pack),
`REALDOOR_CORS_ORIGINS` (comma-separated; default `*`).

- Interactive try-it: **`GET /docs`**
- OpenAPI: **`GET /openapi.json`**
- Health: **`GET /health`** → `{"status":"ok","mode":"openai"|"gold"}`

CORS is enabled via FastAPI's `CORSMiddleware` (Starlette). Preflight
`OPTIONS` and cross-origin browser calls from the future website are allowed.

---

## 1. Challenge format compliance (confirmed)

These shapes were checked against the organizer pack / challenge requirements:

| Concern | Status |
|---------|--------|
| Extract → frozen `ExtractionResponse` (`extraction_contract.py`) | ✅ |
| Flag 3: `ExtractionResponse` → `document_gold.schema.json` via `backend/integration/document_summary_builder.py` (`field_name`→`field`, boxes→`bbox` + `bbox_units: pdf_points`) | ✅ in code |
| 5 document types + allowlisted fields only | ✅ |
| Source boxes: page + coords, bottom-left PDF points, `source_description` | ✅ |
| Low confidence → `value`/`normalized_value` null + `requires_manual_entry` | ✅ |
| Injection → `security_flags: ["prompt_injection_detected"]` (instruction never extracted) | ✅ |
| Reconcile surfaces conflicts; never picks a winner | ✅ |
| Calc is **not** an AI endpoint (FS deterministic MTSP + annualization) | ✅ |
| `/ask` returns grounded answer + `rule_id` + `effective_date` citations | ✅ |
| Readiness → `READY_TO_REVIEW` / `NEEDS_REVIEW` + checklist/next_steps; submission validates `submission.schema.json` | ✅ |
| Safety gate blocks decisioning / scoring / protected-trait / missing citations | ✅ |

---

## 2. `POST /internal/ai/extract`

### Request — `multipart/form-data`

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `file` | file (PDF) | yes | Uploaded document bytes |
| `document_id` | string | yes | Stable id (echoed back) |
| `session_id` | string | yes | Anonymous session token |

```bash
curl -X POST http://127.0.0.1:8000/internal/ai/extract \
  -F "document_id=HH-002-D02" \
  -F "session_id=sess_abc123" \
  -F "file=@paystub.pdf;type=application/pdf"
```

### Response `200` — `ExtractionResponse`

```jsonc
{
  "session_id": "sess_abc123",
  "document": {
    "document_id": "HH-002-D02",
    "document_type": "pay_stub",
    "security_flags": [],
    "fields": [
      {
        "field_name": "gross_pay",
        "value": "$1,395.00",
        "normalized_value": 1395.0,
        "confidence": 0.83,
        "confidence_level": "high",
        "confirmation_status": "awaiting_confirmation",
        "requires_manual_entry": false,
        "source": {
          "page": 1,
          "x1": 340.0, "y1": 526.41, "x2": 393.38, "y2": 542.9,
          "source_description": "'gross pay' on page 1 of the pay stub document"
        }
      }
    ]
  },
  "activity_events": [
    {"timestamp":"2026-07-19T07:25:45+00:00","agent":"document_evidence_agent","action":"load_document","status":"PASS","metadata":{"pages":1,"rasterized":false}},
    {"timestamp":"2026-07-19T07:25:45+00:00","agent":"document_evidence_agent","action":"scan_injection","status":"PASS","metadata":{"flagged":false,"matches":[]}},
    {"timestamp":"2026-07-19T07:25:53+00:00","agent":"document_evidence_agent","action":"classify_document","status":"PASS","metadata":{"document_type":"pay_stub","confidence":0.95}},
    {"timestamp":"2026-07-19T07:25:54+00:00","agent":"document_evidence_agent","action":"extract_fields","status":"PASS","metadata":{"field_count":9,"manual_entry":0}}
  ]
}
```

**Semantics FS must honor**

- `requires_manual_entry: true` / `confidence_level: "low"` → do **not** prefill; `value` and `normalized_value` are `null`.
- Boxes use `pdf_points_bottom_left_origin`. Flip Y for top-left canvas: `y_top = page_height - y2`.
- `security_flags` non-empty → show the security banner (injection never becomes a field).

### Errors

| Situation | Status | Body |
|-----------|--------|------|
| Missing form parts | `422` | FastAPI validation |
| Empty / corrupt PDF | `400` | `{"error_code":"INVALID_DOCUMENT","detail":"..."}` |
| Vision model / missing key | `503` | `{"error_code":"VISION_MODEL_UNAVAILABLE","detail":"..."}` |
| Unsupported type | `200` | `document_type:"unknown"`, `security_flags:["unsupported_document"]` |

---

## 3. `POST /internal/ai/reconcile`

### Request — `application/json`

Send the `document` objects returned by extract (one household):

```jsonc
{
  "documents": [
    {
      "document_id": "HH-002-D02",
      "document_type": "pay_stub",
      "security_flags": [],
      "fields": [
        {
          "field_name": "regular_hours",
          "value": "40",
          "normalized_value": 40,
          "confidence": 0.9,
          "confidence_level": "high",
          "confirmation_status": "awaiting_confirmation",
          "requires_manual_entry": false,
          "source": {
            "page": 1, "x1": 100, "y1": 700, "x2": 140, "y2": 712,
            "source_description": "'regular hours' on page 1 of the pay stub document"
          }
        },
        {
          "field_name": "hourly_rate",
          "value": "$24.00",
          "normalized_value": 24.0,
          "confidence": 0.9,
          "confidence_level": "high",
          "confirmation_status": "awaiting_confirmation",
          "requires_manual_entry": false,
          "source": {
            "page": 1, "x1": 100, "y1": 680, "x2": 140, "y2": 692,
            "source_description": "'hourly rate' on page 1 of the pay stub document"
          }
        },
        {
          "field_name": "gross_pay",
          "value": "$1,395.00",
          "normalized_value": 1395.0,
          "confidence": 0.9,
          "confidence_level": "high",
          "confirmation_status": "awaiting_confirmation",
          "requires_manual_entry": false,
          "source": {
            "page": 1, "x1": 100, "y1": 660, "x2": 160, "y2": 672,
            "source_description": "'gross pay' on page 1 of the pay stub document"
          }
        }
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
      "code": "PAY_STUB_TOTAL_CONFLICT",
      "severity": "blocking_for_confirmation",
      "message": "Pay stub gross pay (1395.0) does not match regular_hours x hourly_rate (40.0 x 24.0 = 960.0). Human confirmation required.",
      "document_ids": ["HH-002-D02"],
      "field_names": ["regular_hours", "hourly_rate", "gross_pay"],
      "observed_values": {
        "regular_hours": 40.0,
        "hourly_rate": 24.0,
        "gross_pay": 1395.0,
        "expected_gross": 960.0
      },
      "source_refs": []
    }
  ],
  "activity_events": [
    {
      "timestamp": "2026-07-19T02:00:05+00:00",
      "agent": "profile_reconciliation_agent",
      "action": "reconcile_documents",
      "status": "ACTION_REQUIRED",
      "metadata": {
        "document_count": 1,
        "conflict_count": 1,
        "conflict_codes": ["PAY_STUB_TOTAL_CONFLICT"]
      }
    }
  ]
}
```

| `code` | Meaning | Default severity |
|--------|---------|------------------|
| `PAY_STUB_TOTAL_CONFLICT` | `hours × rate ≠ gross` on one stub | `blocking_for_confirmation` |
| `PAY_FREQUENCY_CONFLICT` | stubs disagree on frequency | `blocking_for_confirmation` |
| `OVERLAPPING_PAY_PERIODS` | duplicate pay period | `warning` |
| `PERSON_NAME_CONFLICT` | different applicant names | `warning` |

Cross-document conflicts use:

```jsonc
"observed_values": {
  "field": "pay_frequency",
  "per_document": { "HH-002-D02": "weekly", "HH-002-D03": "biweekly" }
}
```

AI never chooses the correct value — FS + renter resolve.

---

## 4. `POST /internal/ai/ask`

Grounded Q&A over the frozen rule corpus. Also used for **calc-view explanation**
(threshold + citation + effective date) — no separate citation route.

### Request — `application/json`

```jsonc
{
  "request": {
    "session_id": "sess_abc123",
    "household_id": "HH-002",
    "question": "What is the frozen 60% income threshold for this household size?"
  },
  "context": {
    "session_id": "sess_abc123",
    "active_household_id": "HH-002",
    "calculation": {
      "household_id": "HH-002",
      "household_size": 2,
      "annualized_income": 49920.0,
      "threshold": 82320.0,
      "comparison": "below_or_equal",
      "formula_steps": [
        {"label": "HH-002-D04:employment_letter", "formula": "40.0 x 24.0 x 52", "result": 49920.0}
      ],
      "calculation_source": "deterministic",
      "rule_year": 2026,
      "citations": []
    }
  }
}
```

### Response `200`

```jsonc
{
  "answer": {
    "status": "SUPPORTED",
    "intent": "THRESHOLD",
    "answer": "The frozen 60% threshold is $82,320 for household size 2.",
    "citations": [
      {
        "rule_id": "HUD-MTSP-002",
        "authority": "hackathon_simulation",
        "effective_date": "2026-05-01",
        "source_url": "...",
        "source_locator": "..."
      }
    ],
    "reasons": [],
    "next_action": null,
    "requires_human_review": false
  },
  "safety": {
    "status": "PASS",
    "safe_to_display": true,
    "checks": { /* same shape as /safety-check */ },
    "violations": []
  },
  "provenance": { /* rule store / retrieval metadata */ },
  "activity_event": {
    "timestamp": "...",
    "agent": "rules_chat_agent",
    "action": "answer_question",
    "status": "PASS",
    "metadata": {}
  }
}
```

`answer.status` is one of `SUPPORTED` | `ABSTAINED` | `REFUSED`. Eligibility /
approval language is refused; insufficient evidence → structured abstention
(`reasons`, `next_action`), never an eligibility label.

### Errors

| Situation | Status | Body |
|-----------|--------|------|
| Invalid body / schema | `400` | `{"error_code":"INVALID_REQUEST","detail":"..."}` |

---

## 5. `POST /internal/ai/readiness`

### Request — `application/json`

Built by FS (or `backend/integration/evaluation_request_builder.py`) after
confirm + reconcile + deterministic calc:

```jsonc
{
  "schema_version": "1.0",
  "request_id": "REQ-HH-002",
  "session_id": "sess_abc123",
  "household_id": "HH-002",
  "consent_confirmed": true,
  "reference_date": "2026-07-18",
  "document_summaries": [
    {
      "document_id": "HH-002-D02",
      "household_id": "HH-002",
      "document_type": "pay_stub",
      "file_name": "hh-002_d02_pay_stub.pdf",
      "synthetic": true,
      "fields": [
        {
          "field": "gross_pay",
          "value": 1395.0,
          "page": 1,
          "bbox": [340.0, 526.41, 393.38, 542.9],
          "bbox_units": "pdf_points"
        }
      ]
    }
  ],
  "confirmed_profile": {
    "household_id": "HH-002",
    "household_size": 2,
    "values": [ /* confirmed field rows with confirmed_by_user */ ]
  },
  "conflicts": [
    {
      "conflict_id": "HH-002-D02:PAY_STUB_TOTAL_CONFLICT",
      "code": "PAY_STUB_TOTAL_CONFLICT",
      "severity": "blocking_for_confirmation",
      "message": "...",
      "document_ids": ["HH-002-D02"],
      "field_names": ["regular_hours", "hourly_rate", "gross_pay"],
      "observed_values": {},
      "source_refs": []
    }
  ],
  "upstream_evidence_gaps": [],
  "calculation_result": {
    "household_id": "HH-002",
    "household_size": 2,
    "annualized_income": 49920.0,
    "threshold": 82320.0,
    "comparison": "below_or_equal",
    "formula_steps": [
      {"label": "HH-002-D04:employment_letter", "formula": "40.0 x 24.0 x 52", "result": 49920.0}
    ],
    "calculation_source": "deterministic",
    "rule_year": 2026,
    "citations": [
      {"rule_id": "HUD-MTSP-002", "effective_date": "2026-05-01"}
    ],
    "calculation_status": "CALCULATED"
  }
}
```

### Response `200`

```jsonc
{
  "household_id": "HH-002",
  "readiness_status": "NEEDS_REVIEW",
  "safety_validation": {
    "status": "PASS",
    "safe_to_display": true,
    "checks": {},
    "violations": []
  },
  "organizer_submission": {
    "household_id": "HH-002",
    "annualized_income": 49920.0,
    "comparison": "below_or_equal",
    "readiness_status": "NEEDS_REVIEW",
    "citations": [
      {"rule_id": "HUD-MTSP-002", "effective_date": "2026-05-01"}
    ],
    "threshold": 82320.0,
    "formula_steps": [],
    "review_reasons": [
      {
        "code": "PAY_STUB_TOTAL_CONFLICT",
        "message": "...",
        "evidence_ids": ["HH-002-D02"],
        "blocks_readiness": true,
        "next_action": "..."
      }
    ],
    "checklist": [
      {
        "item_id": "...",
        "label": "...",
        "status": "NEEDS_REVIEW",
        "reason": "...",
        "evidence_ids": []
      }
    ],
    "next_steps": [
      {"order": 1, "action": "...", "action_type": "USER_REQUIRED"}
    ]
  },
  "provenance": {},
  "activity_event": {}
}
```

`organizer_submission` is validated against `submission.schema.json` before return.
If consent is missing or calc is incomplete → `readiness_status: "NEEDS_REVIEW"`
and `organizer_submission: null`.

---

## 6. `POST /internal/ai/safety-check`

Standalone final gate before any AI output reaches the renter or packet.
(`/ask` and `/readiness` already run safety internally; this endpoint is for
FS to re-gate arbitrary text.)

### Request — `application/json`

```jsonc
{
  "request_text": "",
  "response_text": "NEEDS_REVIEW",
  "citations": [
    {"rule_id": "HUD-MTSP-002", "effective_date": "2026-05-01"}
  ],
  "active_household_id": "HH-002",
  "referenced_household_ids": ["HH-002"],
  "calculation_source": "deterministic",
  "readiness_status": "NEEDS_REVIEW",
  "unconfirmed_values_labelled": true,
  "claims_current_property_availability": false
}
```

### Response `200`

```jsonc
{
  "status": "PASS",
  "safe_to_display": true,
  "checks": {
    "decisioning_claim_present": false,
    "applicant_score_or_ranking_present": false,
    "protected_trait_inference_present": false,
    "cross_household_data_present": false,
    "missing_material_citation": false,
    "non_deterministic_calculation_present": false,
    "unconfirmed_values_unlabelled": false,
    "invalid_readiness_status": false,
    "property_availability_claim_present": false
  },
  "violations": [],
  "replacement_message": null
}
```

`status` is `PASS` or `BLOCKED`. On block, use `replacement_message` (never show
the original unsafe text).

---

## 7. Enum & allowlist reference

- **`document_type`**: `application_summary` | `pay_stub` | `employment_letter` | `benefit_letter` | `gig_statement` | `unknown`
- **`confidence_level`**: `high` (≥0.80) | `medium` (≥0.50) | `low` (<0.50)
- **`confirmation_status`**: AI always emits `awaiting_confirmation`; FS owns the rest
- **`security_flags[]`**: `prompt_injection_detected` | `adversarial_content` | `unsupported_document` | `ocr_failure`
- **`readiness_status`**: `READY_TO_REVIEW` | `NEEDS_REVIEW`
- **`answer.status`**: `SUPPORTED` | `ABSTAINED` | `REFUSED`

| document_type | allowlisted fields |
|---------------|-------------------|
| `application_summary` | `person_name`, `household_size`, `address`, `application_date` |
| `pay_stub` | `person_name`, `pay_date`, `pay_period_start`, `pay_period_end`, `pay_frequency`, `regular_hours`, `hourly_rate`, `gross_pay`, `net_pay` |
| `employment_letter` | `person_name`, `document_date`, `weekly_hours`, `hourly_rate` |
| `benefit_letter` | `person_name`, `document_date`, `monthly_benefit`, `benefit_frequency` |
| `gig_statement` | `person_name`, `statement_month`, `gross_receipts`, `platform_fees` |

---

## 8. Who does what (FS vs AI)

**FS sends:** PDFs + ids on extract; confirmed documents on reconcile; question +
calc context on ask; evaluation request on readiness; text/citations on safety-check.

**FS owns (not AI endpoints):** confirm/edit UI, session state machine, conflict
resolution UI, **deterministic calc** (MTSP CSV + annualization), packet export
against `submission.schema.json`.

**AI owns:** classify/extract/boxes/confidence/injection, conflict *detection*,
grounded Q&A + citations, readiness checklist/status, safety gate.

---

## 9. Suggested call order (per household)

```
1. POST /internal/ai/extract          (once per PDF)
2. [FS] renter confirm / edit
3. POST /internal/ai/reconcile
4. [FS] resolve blocking conflicts
5. [FS] calculate (deterministic — not an AI call)
6. POST /internal/ai/ask              (cite threshold / answer Q&A)
7. POST /internal/ai/readiness
8. POST /internal/ai/safety-check     (before display / packet)
9. [FS] packet export
```

---

*Live implementation: `backend/ai/api.py` (routes), `backend/serve.py` (entrypoint),
`backend/ai/document_evidence/`, `backend/ai/profile_reconciliation/`,
`backend/ai/rules_chat/`, `backend/ai/readiness/`, `backend/ai/safety/`,
`backend/ai/api_adapter.py`. See also `summary.md` for workflow + architecture.*
