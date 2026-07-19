# Homely Path

Homely Path helps households organize housing documents, understand application
readiness, ask grounded questions, and discover public affordable-housing
properties. The repository contains a Flutter client, a Python/FastAPI backend,
Firestore data tooling, and a frozen synthetic evaluation pack.

The backend was originally named **RealDoor AI**, so some modules,
configuration keys, and log messages still use the `REALDOOR_` prefix.

## What the project does

- Extracts allowlisted fields from uploaded housing documents.
- Preserves source evidence, confidence, normalization, and security flags.
- Reconciles conflicting document values without choosing a winner.
- Runs deterministic affordability calculations and readiness checks.
- Answers questions from frozen rules and trusted session results.
- Applies deterministic safety and provenance checks before display.
- Searches public HUD LIHTC properties by location.
- Enriches discovery results with HUD FMR and MTSP references when available.
- Uses Firebase anonymous authentication and session ownership checks.

Homely Path is a review-support tool. It does not determine eligibility,
approval, denial, priority, acceptance probability, or current property
availability.

## Architecture

```text
Flutter application
    |
    | HTTPS + Firebase ID token
    v
FastAPI application
    |-- document extraction and reconciliation
    |-- deterministic calculations and readiness
    |-- grounded rules chat and safety validation
    |-- public property discovery
    |
    +--> OpenAI vision API (real extraction mode)
    +--> Firestore (discovery data and structured chat sessions)
    +--> organizer_pack (rules, synthetic documents, and evaluation gold)
```

The FastAPI application is created in `backend/ai/api.py`. AI clients and OCR
are initialized lazily. Readiness, calculations, reconciliation, citations,
and safety decisions remain deterministic.

## Repository layout

- `frontend/` — Flutter application for web and supported mobile/desktop
  targets.
- `backend/ai/` — document evidence, reconciliation, chat, readiness, safety,
  orchestration, and HTTP routes.
- `backend/calculations/` — deterministic affordability calculations.
- `backend/discovery/` — Firestore-backed public property discovery.
- `backend/integration/` — adapters between documents, calculations,
  readiness, and organizer submissions.
- `contracts/` — shared Python request and response contracts.
- `scripts/` — HUD import, Firestore seed, validation, and inspection tools.
- `tests/` — contracts, integration, adversarial, discovery, and chat tests.
- `organizer_pack/` — frozen synthetic challenge data, rules, schemas, and
  evaluation assets.
- `data/hud/` — ignored local location for official HUD downloads.

## Requirements

- Python 3.11.9
- Flutter with Dart 3.11 or newer
- Firebase CLI for the local Firestore emulator
- An OpenAI API key for real document extraction
- Firebase Admin credentials for production Firestore and authenticated routes

Install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install Flutter dependencies:

```powershell
cd frontend
flutter pub get
```

## Environment configuration

Copy `.env.example` to `.env` and supply only the values needed for your mode.
Important variables include:

- `OPENAI_API_KEY` — required for real extraction mode.
- `REALDOOR_VISION_MODEL` — vision model; defaults to `gpt-4o-mini`.
- `REALDOOR_PACK_ROOT` — organizer pack path; defaults to
  `./organizer_pack`.
- `REALDOOR_CORS_ORIGINS` — comma-separated frontend origin allowlist.
- `REALDOOR_AUTH_ENABLED` — explicit Firebase authentication override.
- `FIREBASE_PROJECT_ID` — Firebase project ID.
- `FIREBASE_SERVICE_ACCOUNT_JSON` — complete service-account JSON for Render
  or another non-Google host.
- `GOOGLE_APPLICATION_CREDENTIALS` — local service-account file path.
- `FIRESTORE_EMULATOR_HOST` — local emulator address.
- `CHATBOT_ENABLED` — enables `/api/chat/answer`.
- `CHAT_SESSION_COLLECTION` — defaults to `chat_sessions`.

Never commit or paste service-account private keys. If a private key is
exposed, revoke it and generate a replacement immediately.

Providing Firebase credentials automatically enables ID-token verification
unless `REALDOOR_AUTH_ENABLED` explicitly overrides it. Protected requests
must send:

```http
Authorization: Bearer <Firebase ID token>
```

For session-scoped routes, the request `session_id` must equal the Firebase
token UID. Health and property discovery remain public.

## Run the backend

Offline gold mode uses the bundled synthetic answers and does not call OpenAI:

```powershell
$env:PYTHONPATH="."
python backend/serve.py --gold
```

Real extraction mode:

```powershell
$env:OPENAI_API_KEY="your-key"
python backend/serve.py
```

The default address is `http://127.0.0.1:8000`.

- API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## Run the Flutter application

The frontend supports three compile-time AI modes: `disabled`, `mock`, and
`http`.

```powershell
cd frontend
flutter run --dart-define=AI_MODE=http --dart-define=AI_BASE_URL=http://127.0.0.1:8000
```

For a web build:

```powershell
cd frontend
flutter build web --no-tree-shake-icons
```

## HTTP API

### `GET /health`

Returns backend liveness and the current `gold` or `openai` mode. It does not
test Firestore or OpenAI connectivity.

### `POST /internal/ai/extract`

Multipart document extraction:

- `document_id`
- `session_id`
- `file` containing a PDF

Returns classified document data, normalized allowlisted fields, source
evidence, confidence, security flags, and activity events.

### `POST /internal/ai/reconcile`

Compares extracted documents and reports conflicts such as pay totals,
frequency, overlapping periods, and person-name differences.

### `POST /internal/ai/ask`

Answers from supplied deterministic results and the frozen rule corpus. The
response includes safety status, citations, provenance, and an activity event.

### `POST /internal/ai/readiness`

Builds a deterministic `READY_TO_REVIEW` or `NEEDS_REVIEW` result with
checklists, reasons, next steps, citations, and an organizer submission.

### `POST /internal/ai/safety-check`

Rejects unsafe or unsupported output, including eligibility decisions,
protected-trait inference, ranking, uncited material claims, cross-household
disclosure, and property-availability claims.

### `POST /api/chat/answer`

Answers a question from a trusted active Firestore session. The route is
disabled unless `CHATBOT_ENABLED=true`.

Example body:

```json
{
  "session_id": "firebase-user-uid",
  "question": "What should I review next?"
}
```

### `GET /api/discovery/properties`

Searches public normalized LIHTC properties in Firestore.

Required query parameter:

- `state` — two-letter state code.

Optional parameters:

- `city`
- `latitude` and `longitude` supplied together
- `radius_miles` from 0 to 100
- `bedrooms` from 0 to 4
- `household_size` from 1 to 8
- `sort_by=alphabetical|distance`

Example:

```text
GET /api/discovery/properties?state=MA&city=Boston
```

Distance search:

```text
GET /api/discovery/properties?state=MA&latitude=42.3601&longitude=-71.0589&radius_miles=25&sort_by=distance
```

The deployed backend is currently configured at:

```text
https://homely-path.onrender.com
```

## Firestore

The trusted backend uses these collections:

- `discovery_properties` — normalized public LIHTC properties.
- `fmr_references` — FY2026 area rent benchmarks.
- `mtsp_references` — FY2026 household-size income references.
- `dataset_versions` — source files, checksums, counts, and import status.
- `chat_sessions` — trusted structured session context for grounded chat.

`firestore.rules` denies all direct client reads and writes. The Flutter client
uses Firebase for authentication, while trusted backend Admin SDK operations
bypass these rules.

### Local emulator

Start Firestore:

```powershell
firebase emulators:start
```

Seed synthetic discovery data:

```powershell
python scripts/bootstrap_firestore.py --project-id homelypath --emulator 127.0.0.1:8080
```

The Firestore emulator runs on port `8080`; its UI runs on port `4000`.

## Discovery data flow

```text
HUD files -> normalization/import scripts -> Firestore -> discovery endpoint
```

The API does not read CSV files directly.

### Bundled Boston sample

The organizer pack includes 32 LIHTC teaching records and one FY2026 MTSP
reference table. It does not include a compatible FMR sample, so sample
properties intentionally have no FMR enrichment.

Validate without credentials:

```powershell
python scripts/import_discovery_samples.py --dry-run
```

Production import:

```powershell
$env:FIREBASE_SERVICE_ACCOUNT_JSON = Get-Content "C:\secure\firebase-service-account.json" -Raw
python scripts/import_discovery_samples.py --project-id homelypath --allow-production-write
python scripts/import_discovery_samples.py --project-id homelypath --verify-only
```

The production flag cannot be used with the emulator. Imports use merge writes
and do not remove stale documents.

### Full official HUD import

Download the official files described in `data/hud/README.md`, then inspect and
import them in reference-first order:

```powershell
python scripts/inspect_hud_files.py
python scripts/import_fmr_firestore.py --dry-run
python scripts/import_mtsp_firestore.py --dry-run
python scripts/import_lihtc_firestore.py --dry-run

python scripts/import_fmr_firestore.py
python scripts/import_mtsp_firestore.py
python scripts/import_lihtc_firestore.py --source-version 2026
python scripts/validate_discovery_import.py --firestore
```

Official source downloads are intentionally ignored by Git.

## Testing

Run the Python suite:

```powershell
python -m pytest
```

Run discovery tests:

```powershell
python -m pytest tests/discovery -q
```

Run Flutter checks:

```powershell
cd frontend
dart format lib test
flutter analyze
flutter test
```

Run the standard-library organizer starter tests:

```powershell
cd organizer_pack\starter
python -m unittest discover -s tests -v
```

Additional backend verification utilities include:

```powershell
python backend/demo.py
python backend/calibrate.py --offline
python backend/verify_endpoints.py
python backend/verify_household_flow.py
python backend/verify_live_http.py http://127.0.0.1:8000
```

## Deployment

`render.yaml` deploys one Python 3.11 FastAPI service.

The build:

1. Installs `requirements.txt`.
2. Fits offline confidence calibration from the organizer pack.

The service then starts the FastAPI application factory with Uvicorn and uses
`/health` as the Render health check.

Required Render secrets include `OPENAI_API_KEY` and
`FIREBASE_SERVICE_ACCOUNT_JSON`. Restrict `REALDOOR_CORS_ORIGINS` to the
deployed frontend origins before production release.

## Safety and privacy

- All bundled applicant identities and documents are synthetic.
- Uploaded document content is treated as untrusted.
- Protected or sensitive traits must not be inferred.
- The system must not make housing decisions or rank applicants/properties.
- Discovery availability is always presented as unknown.
- FMR values are area benchmarks, not property rents.
- MTSP values are references, not eligibility determinations.
- Raw applicant files must not be added to the organizer pack or repository.

See `organizer_pack/governance/DATA_USE_AND_SAFETY.md` for the complete
challenge-data constraints.

## Current limitations

- The bundled property list is a teaching subset, not a complete inventory.
- The bundled sample has no compatible FMR reference file.
- Property availability, rents, waitlists, and application status are unknown.
- Discovery depends on Firestore being imported separately from deployment.
- Imports merge records and do not automatically delete stale data.
- CORS defaults to `*` until production origins are configured.
- The organizer pack is draft and not approved for external distribution.
- Some richer frontend reconciliation, provenance, export, and readiness flows
  remain incomplete.

## License and data use

Review `organizer_pack/governance/LICENSE_MANIFEST.csv` and
`organizer_pack/governance/ORGANIZER_APPROVALS.md` before distributing the
organizer pack or derived assets. Repository code and bundled datasets should
not be assumed to have a single distribution license unless one is added
explicitly.
