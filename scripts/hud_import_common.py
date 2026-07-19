"""Shared helpers for deterministic HUD file imports."""

from __future__ import annotations

import hashlib
import io
import math
import re
import zipfile
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def clean_string(value: Any) -> str | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = str(value).strip()
    return None if not text or text.casefold() in {"nan", "none", "null"} else text


def clean_code(value: Any, *, width: int | None = None) -> str | None:
    """Preserve identifiers as strings and restore leading zeroes if requested."""
    text = clean_string(value)
    if text is None:
        return None
    if re.fullmatch(r"-?\d+\.0+", text):
        text = text.split(".", 1)[0]
    if width and text.isdigit():
        text = text.zfill(width)
    return text


def clean_integer(value: Any) -> int | None:
    try:
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return None
        number = float(value)
        return int(number) if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def clean_float(value: Any) -> float | None:
    try:
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def clean_coordinate(value: Any, *, latitude: bool) -> float | None:
    number = clean_float(value)
    lower, upper = (-90, 90) if latitude else (-180, 180)
    return number if number is not None and lower <= number <= upper else None


def resolve_columns(
    columns: Iterable[str],
    aliases: Mapping[str, Iterable[str]],
) -> dict[str, str]:
    """Resolve normalized fields against real, inspected source headers."""
    actual = {str(column).strip().casefold(): str(column) for column in columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for field, candidates in aliases.items():
        match = next(
            (actual[candidate.strip().casefold()] for candidate in candidates
             if candidate.strip().casefold() in actual),
            None,
        )
        if match is None:
            missing.append(f"{field} ({', '.join(candidates)})")
        else:
            resolved[field] = match
    if missing:
        raise ValueError(
            "Source columns changed or were not inspected. Missing mappings: "
            + "; ".join(missing)
        )
    return resolved


def read_hud_excel(
    path: Path,
    *,
    sheet_name: str | int = 0,
    nrows: int | None = None,
    dtype: Any = None,
) -> pd.DataFrame:
    """Read an official HUD workbook, repairing known invalid metadata XML.

    HUD's current LIHTC and revised FY2026 FMR workbooks contain harmless XML
    metadata that strict openpyxl versions reject. The source file is never
    changed; a repaired in-memory copy is passed to pandas.
    """
    try:
        return pd.read_excel(
            path, sheet_name=sheet_name, nrows=nrows, dtype=dtype
        )
    except (TypeError, ValueError) as original_error:
        try:
            repaired = _repaired_workbook(path)
        except zipfile.BadZipFile:
            raise original_error
        return pd.read_excel(
            repaired, sheet_name=sheet_name, nrows=nrows, dtype=dtype
        )


def _repaired_workbook(path: Path) -> io.BytesIO:
    source = zipfile.ZipFile(path)
    repaired = io.BytesIO()
    with source, zipfile.ZipFile(repaired, "w", zipfile.ZIP_DEFLATED) as output:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.endswith(".xml"):
                text = data.decode("utf-8")
                text = re.sub(r'\s+synchVertical="[^"]*"', "", text)
                text = re.sub(r'\s+synchHorizontal="[^"]*"', "", text)
                text = re.sub(
                    r"(\d{4})-\s+(\d)-(\d{2}T)",
                    r"\1-0\2-\3",
                    text,
                )
                data = text.encode("utf-8")
            output.writestr(info, data)
    repaired.seek(0)
    return repaired


def excel_sheet_names(path: Path) -> list[str]:
    """Return sheet names using the same resilient workbook repair."""
    try:
        return pd.ExcelFile(path).sheet_names
    except (TypeError, ValueError):
        return pd.ExcelFile(_repaired_workbook(path)).sheet_names


def checksum_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_documents(
    db,
    *,
    collection_name: str,
    documents: Iterable[tuple[str, dict[str, Any]]],
    batch_size: int = 300,
) -> int:
    if not 1 <= batch_size <= 500:
        raise ValueError("batch_size must be between 1 and Firestore's limit of 500")
    batch = db.batch()
    pending = 0
    total = 0
    for document_id, payload in documents:
        reference = db.collection(collection_name).document(document_id)
        batch.set(reference, payload, merge=True)
        pending += 1
        total += 1
        if pending >= batch_size:
            batch.commit()
            batch = db.batch()
            pending = 0
    if pending:
        batch.commit()
    return total


def write_dataset_version(
    db,
    *,
    document_id: str,
    dataset_name: str,
    source_file: Path,
    source_page: str,
    record_count: int,
    source_year: int | None = None,
    fiscal_year: int | None = None,
    validation_errors: list[str] | None = None,
) -> None:
    errors = validation_errors or []
    db.collection("dataset_versions").document(document_id).set(
        {
            "dataset_name": dataset_name,
            "source_year": source_year,
            "fiscal_year": fiscal_year,
            "source_file": source_file.name,
            "source_page": source_page,
            "checksum_sha256": checksum_sha256(source_file),
            "record_count": record_count,
            "imported_at": datetime.now(timezone.utc),
            "status": "ACTIVE" if not errors else "INVALID",
            "validation_errors": errors,
        }
    )
