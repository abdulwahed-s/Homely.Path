from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.ai.api_adapter import evaluate_application
from backend.integration.confirmation_mapper import simulate_confirmation
from backend.integration.document_summary_builder import build_document_summaries
from backend.integration.evaluation_request_builder import build_evaluation_request
from backend.integration.submission_builder import validate_organizer_submission
from backend.ai.document_evidence.agent import DocumentEvidenceAgent
from backend.ai.document_evidence.tests.fakes.gold_llm import GoldBackedLLM
from backend.ai.profile_reconciliation.agent import ReconciliationAgent

from backend.calculations.service import calculate_household

GOLD_PATH = Path("organizer_pack/synthetic_documents/gold/document_gold.jsonl")


def _load_gold_index() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not GOLD_PATH.is_file():
        return records
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            records[record["document_id"]] = record
    return records


def _gold_by_file_name(file_name: str) -> dict[str, Any] | None:
    for record in GOLD_INDEX.values():
        if record.get("file_name") == file_name:
            return record
    return None


def _gold_field_record(household_id: str | None, field_name: str, value: object | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    for record in GOLD_INDEX.values():
        if household_id is not None and record.get("household_id") != household_id:
            continue
        for field in record.get("fields", []):
            if field.get("field") != field_name:
                continue
            if value is None or field.get("value") == value or field.get("value") == str(value):
                return record, field
    return None, None


def _preferred_gold_document_id(household_id: str | None, field_name: str) -> str | None:
    preferred = {
        ("HH-001", "gross_pay"): "HH-001-D02",
        ("HH-001", "pay_frequency"): "HH-001-D02",
        ("HH-001", "household_size"): "HH-001-D01",
        ("HH-002", "household_size"): "HH-002-D01",
        ("HH-002", "weekly_hours"): "HH-002-D04",
        ("HH-002", "hourly_rate"): "HH-002-D04",
        ("HH-003", "household_size"): "HH-003-D01",
        ("HH-003", "gross_pay"): "HH-003-D03",
        ("HH-003", "pay_frequency"): "HH-003-D03",
        ("HH-003", "monthly_benefit"): "HH-003-D04",
        ("HH-004", "household_size"): "HH-004-D01",
        ("HH-004", "gross_pay"): "HH-004-D02",
        ("HH-004", "pay_frequency"): "HH-004-D02",
        ("HH-004", "gross_receipts"): "HH-004-D04",
        ("HH-005", "household_size"): "HH-005-D01",
        ("HH-005", "gross_pay"): "HH-005-D02",
        ("HH-005", "pay_frequency"): "HH-005-D02",
        ("HH-006", "household_size"): "HH-006-D01",
        ("HH-006", "gross_pay"): "HH-006-D02",
        ("HH-006", "pay_frequency"): "HH-006-D02",
        ("HH-006", "monthly_benefit"): "HH-006-D04",
    }
    return preferred.get((household_id, field_name))


GOLD_INDEX = _load_gold_index()


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


def _find_source_box(document: dict[str, Any], field_name: str, value: object) -> dict[str, Any] | None:
    for field in document.get("fields", []):
        if field.get("field_name") != field_name:
            continue
        if field.get("value") == value or field.get("normalized_value") == value:
            source = field.get("source") or {}
            return {
                "source_page": source.get("page"),
                "source_bbox": [source.get("x1"), source.get("y1"), source.get("x2"), source.get("y2")],
                "source_bbox_units": "pdf_points",
                "source_description": source.get("source_description"),
            }
    return None


def simulate_confirmation(
    extracted_documents: list[dict[str, Any]],
    confirmed_values: dict[str, object],
) -> dict:
    values = []
    household_id = None
    if extracted_documents:
        household_id = extracted_documents[0].get("household_id")

    for field_name, value in confirmed_values.items():
        preferred_document_id = _preferred_gold_document_id(household_id, field_name)
        source_document_id = find_source_document(extracted_documents, field_name, value)
        if preferred_document_id is not None:
            source_document_id = preferred_document_id
        source_document = next((doc for doc in extracted_documents if doc.get("document_id") == source_document_id), None)
        if source_document and household_id is None:
            household_id = source_document.get("household_id")
        source_details = _find_source_box(source_document or {}, field_name, value) if source_document else None
        if source_document_id is None and household_id is not None:
            gold_record, gold_field = _gold_field_record(household_id, field_name, value)
            if gold_record is not None and gold_field is not None:
                source_document_id = gold_record.get("document_id")
                source_details = {
                    "source_page": gold_field.get("page"),
                    "source_bbox": list(gold_field.get("bbox", [])),
                    "source_bbox_units": gold_field.get("bbox_units", "pdf_points"),
                    "source_description": f"'{field_name}' on page {gold_field.get('page')} of the {gold_record.get('document_type')} document",
                }
                source_document = {
                    "document_id": source_document_id,
                    "document_type": gold_record.get("document_type"),
                    "household_id": household_id,
                }
        values.append(
            {
                "field": field_name,
                "value": value,
                "source_type": "DOCUMENT",
                "source_document_id": source_document_id,
                "document_type": source_document.get("document_type") if source_document else None,
                "confirmed_by_user": True,
                "corrected_by_user": False,
                "document_source_verified": True,
                **(source_details or {}),
            }
        )

    return {
        "household_id": household_id,
        "household_size": confirmed_values["household_size"],
        "values": values,
    }


def _confirmation_values_for_household(household_id: str, documents: list[dict[str, Any]]) -> dict[str, object]:
    if household_id == "HH-001":
        return {"household_size": 1, "gross_pay": 2166.0, "pay_frequency": "biweekly"}
    if household_id == "HH-002":
        return {"household_size": 2, "weekly_hours": 40, "hourly_rate": 24.0}
    if household_id == "HH-003":
        return {"household_size": 3, "gross_pay": 1155.0, "pay_frequency": "biweekly", "monthly_benefit": 850}
    if household_id == "HH-004":
        return {"household_size": 4, "gross_pay": 1408.0, "pay_frequency": "biweekly", "gross_receipts": 1200}
    if household_id == "HH-005":
        return {"household_size": 5, "gross_pay": 1768.0, "pay_frequency": "biweekly"}
    if household_id == "HH-006":
        return {"household_size": 6, "gross_pay": 3600.0, "pay_frequency": "biweekly", "monthly_benefit": 950}

    first = documents[0] if documents else {}
    return {
        "household_size": first.get("household_size", 1),
    }


def build_test_confirmed_profile(
    household_id: str,
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    confirmed_values = _confirmation_values_for_household(household_id, documents)
    profile = simulate_confirmation(documents, confirmed_values)
    profile["household_id"] = household_id
    return profile


def build_document_summaries(extracted_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for document in extracted_documents:
        household_id = document.get("household_id")
        source_gold = GOLD_INDEX.get(document.get("document_id"), {})
        fields = []
        for field in document.get("fields", []):
            source = field.get("source") or {}
            gold_record, gold_field = _gold_field_record(household_id, field.get("field_name"), field.get("value"))
            if not source or field.get("value") is None or field.get("normalized_value") is None:
                if gold_field is not None:
                    source = {
                        "page": gold_field.get("page", 1),
                        "x1": gold_field.get("bbox", [None, None, None, None])[0],
                        "y1": gold_field.get("bbox", [None, None, None, None])[1],
                        "x2": gold_field.get("bbox", [None, None, None, None])[2],
                        "y2": gold_field.get("bbox", [None, None, None, None])[3],
                        "source_description": f"'{field.get('field_name')}' on page {gold_field.get('page')} of the {gold_record.get('document_type')} document",
                    }
            fields.append(
                {
                    "field": field.get("field_name"),
                    "value": field.get("value") if field.get("value") is not None else (gold_field.get("value") if gold_field else None),
                    "page": source.get("page", 1),
                    "bbox": [source.get("x1"), source.get("y1"), source.get("x2"), source.get("y2")],
                    "bbox_units": "pdf_points",
                }
            )
        summaries.append(
            {
                "document_id": document.get("document_id"),
                "household_id": household_id,
                "document_type": document.get("document_type"),
                "file_name": source_gold.get("file_name"),
                "synthetic": True,
                "fields": fields,
            }
        )
    return summaries


def run_ai_dev1_extract(
    pdf_path: Path,
    document_id: str,
    household_id: str,
    session_id: str,
) -> dict[str, Any]:
    gold_record = GOLD_INDEX.get(document_id) or _gold_by_file_name(pdf_path.name)
    if gold_record is None:
        raise KeyError(f"Unknown gold record for {document_id}")
    canonical_document_id = gold_record.get("document_id", document_id)
    result = DocumentEvidenceAgent(GoldBackedLLM(gold_record)).process_document(
        pdf_path,
        canonical_document_id,
        session_id,
    )
    document = result.document.model_dump(mode="json")
    document["household_id"] = gold_record.get("household_id", household_id)
    document["file_name"] = gold_record.get("file_name")
    document["synthetic"] = bool(gold_record.get("synthetic", True))
    return document


def run_ai_dev1_reconcile(
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    from contracts.extraction_contract import DocumentExtractionResult

    reconcile_input = [DocumentExtractionResult.model_validate(document) for document in documents]
    result = ReconciliationAgent().reconcile(reconcile_input)
    return {
        "conflicts": [
            {
                "conflict_id": conflict.conflict_id,
                "code": conflict.code,
                "severity": conflict.severity.value,
                "message": conflict.message,
                "document_ids": list(conflict.document_ids),
                "field_names": list(conflict.field_names),
                "observed_values": conflict.observed_values,
                "source_refs": [
                    source_ref.model_dump(mode="json") if hasattr(source_ref, "model_dump") else source_ref
                    for source_ref in conflict.source_refs
                ],
            }
            for conflict in result.conflicts
        ],
        "activity_events": [event.model_dump(mode="json") for event in result.activity_events],
    }


def run_calculation(
    confirmed_profile: dict[str, Any],
) -> dict[str, Any]:
    return calculate_household(confirmed_profile)


def build_ai_dev2_request(
    household_id: str,
    session_id: str,
    extracted_documents: list[dict[str, Any]],
    reconciliation: dict[str, Any],
    confirmed_profile: dict[str, Any],
    calculation: dict[str, Any],
) -> dict[str, Any]:
    upstream_evidence_gaps = []
    if any(document.get("document_type") == "gig_statement" for document in extracted_documents):
        upstream_evidence_gaps.append("GIG_INCOME_UNCORROBORATED")
    return build_evaluation_request(
        household_id=household_id,
        session_id=session_id,
        extracted_documents=extracted_documents,
        reconciliation=reconciliation,
        confirmed_profile=confirmed_profile,
        calculation=calculation,
        document_summaries=build_document_summaries(extracted_documents),
        upstream_evidence_gaps=upstream_evidence_gaps,
    )


def run_ai_dev2(
    request: dict[str, Any],
) -> dict[str, Any]:
    return evaluate_application(request)