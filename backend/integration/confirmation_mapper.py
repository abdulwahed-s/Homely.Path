from __future__ import annotations

from typing import Any


def find_source_document(
    extracted_documents: list[dict[str, Any]],
    field_name: str,
    value: object,
) -> str | None:
    for document in extracted_documents:
        for field in document.get("fields", []):
            if field.get("field_name") != field_name:
                continue
            if field.get("value") == value or field.get("normalized_value") == value:
                return document.get("document_id")
    return None


def simulate_confirmation(
    extracted_documents: list[dict[str, Any]],
    confirmed_values: dict[str, object],
) -> dict:
    values = []
    household_id = extracted_documents[0].get("household_id") if extracted_documents else None

    for field_name, value in confirmed_values.items():
        source_document_id = find_source_document(extracted_documents, field_name, value)
        source_document = next((doc for doc in extracted_documents if doc.get("document_id") == source_document_id), None)
        if source_document and household_id is None:
            household_id = source_document.get("household_id")

        source_details = None
        if source_document is not None:
            for field in source_document.get("fields", []):
                if field.get("field_name") != field_name:
                    continue
                if field.get("value") == value or field.get("normalized_value") == value:
                    source = field.get("source") or {}
                    source_details = {
                        "source_page": source.get("page"),
                        "source_bbox": [source.get("x1"), source.get("y1"), source.get("x2"), source.get("y2")],
                        "source_bbox_units": "pdf_points",
                        "source_description": source.get("source_description"),
                    }
                    break

        values.append({
            "field": field_name,
            "value": value,
            "source_type": "DOCUMENT",
            "source_document_id": source_document_id,
            "document_type": source_document.get("document_type") if source_document else None,
            "confirmed_by_user": True,
            "corrected_by_user": False,
            "document_source_verified": True,
            **(source_details or {}),
        })

    return {
        "household_id": household_id,
        "household_size": confirmed_values["household_size"],
        "values": values,
    }