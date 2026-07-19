# Backend contract notes

Re-inspected on 2026-07-19 from `../backend/ai/api.py` and the deployed service
at `https://homely-path.onrender.com` (OpenAPI title: `RealDoor AI Service`,
version `1.1`).

## Exposed routes

- `GET /health` returns `{ "status": "ok", "mode": "openai" | "gold" }`.
- `POST /internal/ai/extract` accepts multipart `file`, `document_id`, and
  `session_id`. It returns `{ session_id, document, activity_events }`.
  PDF coordinates are points with a bottom-left origin.
- `POST /internal/ai/reconcile` accepts
  `{ "session_id", "documents": [DocumentExtractionResult] }` and returns
  `{ conflicts, activity_events }`.
- `POST /internal/ai/ask` accepts `{ request, context }`. It returns a grounded
  answer, citations/effective dates where applicable, a safety decision,
  provenance, and an activity event.
- `POST /internal/ai/readiness` accepts the documented evaluation payload
  (confirmed profile, document summaries, conflicts, evidence gaps, and the
  deterministic calculation). It returns a readiness status, safety validation,
  organizer submission, provenance, and an activity event.
- `POST /internal/ai/safety-check` accepts text, citations, household scope,
  calculation provenance, readiness state, and labelling flags. It returns
  `PASS`/`BLOCKED`, `safe_to_display`, checks, violations, and a replacement
  message when blocked.

## Live smoke check

The deployed service returned successful responses for health, ask,
safety-check, one PDF extraction from `test_documents`, reconciliation of that
extraction, and readiness. The incomplete readiness smoke payload returned
`NEEDS_REVIEW` and `safe_to_display: false`, as expected for a final gate.
With a contract-valid deterministic calculation for household size two and the
`HUD-MTSP-002` citation, live `/ask` returned `SUPPORTED` and live `/readiness`
returned `READY_TO_REVIEW`. Therefore `ABSTAINED` and `NEEDS_REVIEW` are
evidence states, not HTTP mock fallbacks: they are expected until the renter has
confirmed the required information and the calculation has a material citation.

## Integration and deployment constraints

- CORS middleware is present; its default origin allowlist is `*`, with
  `REALDOOR_CORS_ORIGINS` available for deployment configuration.
- The authenticated backend requires a Firebase bearer token and enforces
  `session_id == token.uid`. Flutter supplies a fresh Firebase token, checks the
  active UID locally, and now includes the session ID on every authenticated
  route. Deploy the verified `backend_new` service with Firebase credentials;
  the older deployed service may not yet contain this middleware.
- Extract/reconcile use FastAPI validation (`422`) and structured `400` bodies
  for invalid input. Extract also reports `503` when the vision model is
  unavailable and catches unexpected extraction failures as structured `500`s.
- The Flutter extraction and reconciliation DTOs already match the current
  response wrappers. Rules, readiness, and safety are now valid HTTP backend
  capabilities; client feature wiring is a separate product/UI task.
- The service must be configured with `AI_MODE=http` and `AI_BASE_URL` at
  runtime; the app intentionally does not hardcode a local server address.
