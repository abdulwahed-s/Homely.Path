from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


def resolve_pack_root(pack_root: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if pack_root is not None:
        candidates.append(Path(pack_root))
    candidates.extend([
        Path("organizer_pack"),
        Path("realdoor-hackathon-starter-pack") / "organizer_pack",
    ])

    for candidate in candidates:
        if (candidate / "data" / "mtsp_2026_boston_cambridge_quincy.csv").is_file():
            return candidate.resolve()

    raise FileNotFoundError("Could not find the organizer pack MTSP table.")


@lru_cache(maxsize=4)
def _load_rows(pack_root: str) -> tuple[dict[str, str], ...]:
    root = resolve_pack_root(pack_root)
    csv_path = root / "data" / "mtsp_2026_boston_cambridge_quincy.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def lookup_row(household_size: int, pack_root: str | Path | None = None) -> dict[str, str] | None:
    rows = _load_rows(str(resolve_pack_root(pack_root)))
    for row in rows:
        if int(row["household_size"]) == int(household_size):
            return dict(row)
    return None


def lookup_threshold(household_size: int, pack_root: str | Path | None = None) -> float | None:
    row = lookup_row(household_size, pack_root)
    if row is None:
        return None
    return float(row["core_challenge_threshold"])