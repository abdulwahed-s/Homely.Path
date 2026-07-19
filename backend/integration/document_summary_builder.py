from __future__ import annotations

from typing import Any


def build_document_summaries(extracted_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for document in extracted_documents:
        summaries.append(
            {
                "document_id": document.get("document_id"),
                "household_id": document.get("household_id"),
                "document_type": document.get("document_type"),
                "file_name": document.get("file_name"),
                "synthetic": document.get("synthetic", True),
                "fields": [
                    {
                        "field": field.get("field_name"),
                        "value": field.get("value"),
                        "page": (field.get("source") or {}).get("page", 1),
                        "bbox": [
                            (field.get("source") or {}).get("x1"),
                            (field.get("source") or {}).get("y1"),
                            (field.get("source") or {}).get("x2"),
                            (field.get("source") or {}).get("y2"),
                        ],
                        "bbox_units": "pdf_points",
                    }
                    for field in document.get("fields", [])
                ],
            }
        )
    return summaries