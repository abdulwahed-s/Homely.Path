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
