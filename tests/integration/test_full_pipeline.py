from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.contracts.test_handoff_contracts import validate_organizer_submission
from tests.integration.adapters import (
    build_ai_dev2_request,
    build_document_summaries,
    build_test_confirmed_profile,
    run_ai_dev1_extract,
    run_ai_dev1_reconcile,
    run_ai_dev2,
    run_calculation,
)


def _load_checklists() -> dict[str, dict]:
    path = Path("organizer_pack/evaluation/application_checklists.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["household_id"]: row for row in rows}


CHECKLISTS = _load_checklists()


def _run_complete_pipeline(household_id: str) -> dict:
    session_id = "TEST-SESSION-001"
    document_paths = sorted(Path("organizer_pack/synthetic_documents/documents").glob(f"{household_id.lower()}*.pdf"))

    extracted_documents = []
    for pdf_path in document_paths:
        document_id = pdf_path.stem.upper().replace("_", "-")
        result = run_ai_dev1_extract(
            pdf_path=pdf_path,
            document_id=document_id,
            household_id=household_id,
            session_id=session_id,
        )
        extracted_documents.append(result)

    reconciliation = run_ai_dev1_reconcile(extracted_documents)
    confirmed_profile = build_test_confirmed_profile(household_id=household_id, documents=extracted_documents)
    calculation = run_calculation(confirmed_profile)
    request = build_ai_dev2_request(
        household_id=household_id,
        session_id=session_id,
        extracted_documents=extracted_documents,
        reconciliation=reconciliation,
        confirmed_profile=confirmed_profile,
        calculation=calculation,
    )
    response = run_ai_dev2(request)
    response["_request_payload"] = request
    response["_extracted_documents"] = extracted_documents
    return response


@pytest.mark.parametrize("household_id", ["HH-001", "HH-002", "HH-003", "HH-004", "HH-005", "HH-006"])
def test_household_end_to_end(household_id):
    response = _run_complete_pipeline(household_id)

    assert response["household_id"] == household_id
    assert response["safety_validation"]["safe_to_display"]


def test_complete_household_pipeline_hh001():
    response = _run_complete_pipeline("HH-001")
    expected = CHECKLISTS["HH-001"]

    assert response["household_id"] == "HH-001"
    assert response["organizer_submission"]["annualized_income"] == pytest.approx(expected["expected_annualized_income"])
    assert response["readiness_status"] == expected["expected_readiness_status"]
    assert [reason["code"] for reason in response["organizer_submission"]["review_reasons"]] == expected["expected_review_reasons"]
    validate_organizer_submission(response)


def test_conflicting_pay_totals_hh002():
    response = _run_complete_pipeline("HH-002")

    assert response["readiness_status"] == "NEEDS_REVIEW"
    assert any(reason["code"] == "PAY_STUB_TOTAL_CONFLICT" for reason in response["organizer_submission"]["review_reasons"])
    assert response["organizer_submission"]["annualized_income"] == pytest.approx(CHECKLISTS["HH-002"]["expected_annualized_income"])


def test_gig_income_hh004():
    response = _run_complete_pipeline("HH-004")

    assert response["readiness_status"] == "NEEDS_REVIEW"
    assert any(reason["code"] == "GIG_INCOME_UNCORROBORATED" for reason in response["organizer_submission"]["review_reasons"])


def test_expired_document_hh005():
    response = _run_complete_pipeline("HH-005")

    assert response["readiness_status"] == "NEEDS_REVIEW"
    assert any(reason["code"] == "EMPLOYMENT_LETTER_EXPIRED" for reason in response["organizer_submission"]["review_reasons"])


def test_household_size_outside_table():
    result = run_calculation({
        "household_id": "HH-009",
        "household_size": 9,
        "values": [
            {"field": "gross_pay", "value": 1000.0, "source_document_id": "HH-009-D02", "document_type": "pay_stub", "source_page": 1, "source_bbox": [1, 1, 2, 2], "source_bbox_units": "pdf_points"},
            {"field": "pay_frequency", "value": "weekly", "source_document_id": "HH-009-D02", "document_type": "pay_stub", "source_page": 1, "source_bbox": [1, 1, 2, 2], "source_bbox_units": "pdf_points"},
        ],
    })

    assert result["comparison"] == "no_frozen_threshold"


def test_missing_calculation_input():
    response = _run_complete_pipeline("HH-001")
    request = response["_request_payload"]
    request["confirmed_profile"]["values"] = [item for item in request["confirmed_profile"]["values"] if item["field"] != "pay_frequency"]
    request["calculation_result"] = run_calculation(request["confirmed_profile"])
    incomplete = run_ai_dev2(request)

    assert incomplete["readiness_status"] == "NEEDS_REVIEW"
    assert incomplete["organizer_submission"] is None