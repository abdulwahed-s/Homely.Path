from __future__ import annotations

from backend.integration.evaluation_request_builder import build_evaluation_request


def test_build_evaluation_request_uses_explicit_summaries_and_gaps() -> None:
    document_summaries = [
        {
            "document_id": "DOC-1",
            "household_id": "HH-001",
            "document_type": "pay_stub",
            "file_name": "pay_stub.pdf",
            "synthetic": True,
            "fields": [],
        }
    ]
    request = build_evaluation_request(
        household_id="HH-001",
        session_id="SESSION-1",
        extracted_documents=[{"document_id": "DOC-1", "document_type": "pay_stub", "fields": []}],
        reconciliation={"conflicts": [{"conflict_id": "C-1"}]},
        confirmed_profile={"household_id": "HH-001"},
        calculation={"gross_income": 40230},
        document_summaries=document_summaries,
        upstream_evidence_gaps=["GIG_INCOME_UNCORROBORATED"],
    )

    assert request["request_id"] == "REQ-HH-001"
    assert request["document_summaries"] == document_summaries
    assert request["conflicts"] == [{"conflict_id": "C-1"}]
    assert request["upstream_evidence_gaps"] == ["GIG_INCOME_UNCORROBORATED"]
    assert request["calculation_result"] == {"gross_income": 40230}


def test_build_evaluation_request_falls_back_to_document_summaries() -> None:
    request = build_evaluation_request(
        household_id="HH-002",
        session_id="SESSION-2",
        extracted_documents=[{"document_id": "DOC-2", "document_type": "pay_stub", "fields": []}],
        reconciliation={},
        confirmed_profile={"household_id": "HH-002"},
        calculation={"gross_income": 12345},
    )

    assert request["document_summaries"] == [
        {
            "document_id": "DOC-2",
            "household_id": None,
            "document_type": "pay_stub",
            "file_name": None,
            "synthetic": True,
            "fields": [],
        }
    ]