"""Print real HUD workbook sheets, headers, and representative rows."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hud_import_common import excel_sheet_names, read_hud_excel  # noqa: E402

HUD = ROOT / "data" / "hud"


def inspect_csv(path: Path) -> None:
    frame = pd.read_csv(path, nrows=5, low_memory=False, dtype=str)
    print(f"\nCSV: {path}")
    print("Columns:")
    for column in frame.columns:
        print(f"- {column}")
    print("\nSample:")
    print(frame.head().to_string(index=False))


def inspect_excel(path: Path) -> None:
    print(f"\nExcel: {path}")
    sheets = excel_sheet_names(path)
    print("Sheets:", sheets)
    for sheet in sheets:
        frame = read_hud_excel(path, sheet_name=sheet, nrows=5)
        print(f"\nSheet: {sheet}")
        print("Columns:")
        for column in frame.columns:
            print(f"- {column}")
        print("\nSample:")
        print(frame.head().to_string(index=False))


def inspect_lihtc() -> None:
    csv_path = HUD / "lihtc" / "LIHTCPUB.CSV"
    xlsx_path = HUD / "lihtc" / "LIHTCPUB.xlsx"
    if csv_path.exists():
        inspect_csv(csv_path)
    elif xlsx_path.exists():
        # The current May 2026 archive provides XLSX rather than the CSV named
        # on older HUD documentation.
        inspect_excel(xlsx_path)
    else:
        raise FileNotFoundError(f"LIHTC source not found at {csv_path} or {xlsx_path}")


if __name__ == "__main__":
    inspect_lihtc()
    inspect_excel(HUD / "fmr" / "FY2026_FMR_County.xlsx")
    inspect_excel(HUD / "mtsp" / "FY2026_MTSP.xlsx")
