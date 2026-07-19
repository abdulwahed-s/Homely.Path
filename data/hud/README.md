# HUD discovery source files

Raw HUD downloads are intentionally gitignored. Download and place:

- current LIHTC archive contents at `lihtc/LIHTCPUB.xlsx` (the May 2026
  `LIHTCPUB.ZIP` currently contains XLSX, despite older documentation referring
  to `LIHTCPUB.CSV`);
- revised FY 2026 county-level FMR workbook at
  `fmr/FY2026_FMR_County.xlsx`;
- FY 2026 MTSP limits workbook at `mtsp/FY2026_MTSP.xlsx`.

Official sources:

- <https://www.huduser.gov/portal/datasets/lihtc/property.html>
- <https://www.huduser.gov/portal/datasets/fmr.html>
- <https://www.huduser.gov/portal/datasets/mtsp.html>

Inspect real columns before import:

```powershell
python scripts/inspect_hud_files.py
```

Import in reference-first order:

```powershell
python scripts/import_fmr_firestore.py
python scripts/import_mtsp_firestore.py
python scripts/import_lihtc_firestore.py
python scripts/validate_discovery_import.py --firestore
```

Use `--dry-run` on any importer to validate normalization without writing to
Firestore. The scripts use batched writes and record checksums/counts in
`dataset_versions`.

## Bundled Boston sample

The committed organizer pack contains a small LIHTC property sample and an
MTSP reference table. It does not contain a compatible FMR table, so this path
intentionally leaves FMR enrichment empty.

Validate the bundled files without credentials:

```powershell
python scripts/import_discovery_samples.py --dry-run
```

For a one-time production import, download a Firebase Admin service-account
JSON for the intended project and keep it outside the repository. Then run:

```powershell
$env:FIREBASE_SERVICE_ACCOUNT_JSON = Get-Content "C:\secure\firebase-service-account.json" -Raw
python scripts/import_discovery_samples.py --project-id homelypath --allow-production-write
python scripts/import_discovery_samples.py --project-id homelypath --verify-only
```

The production flag is deliberately incompatible with the emulator. The
import uses merge writes and can be rerun, but it does not delete stale
documents.

Configure the Render service with the same `FIREBASE_PROJECT_ID` and
`FIREBASE_SERVICE_ACCOUNT_JSON` values, redeploy, and smoke-test:

```powershell
Invoke-RestMethod "https://homely-path.onrender.com/api/discovery/properties?state=MA&city=Boston"
Invoke-RestMethod "https://homely-path.onrender.com/api/discovery/properties?state=MA&latitude=42.3601&longitude=-71.0589&radius_miles=25&sort_by=distance"
```

Never commit the service-account JSON. Supplying Firebase credentials also
enables authentication on `/internal/ai/*`; the discovery route remains public.
