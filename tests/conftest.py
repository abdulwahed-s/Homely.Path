from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.integration.adapters import (
    build_ai_dev2_request,
    build_test_confirmed_profile,
    run_ai_dev1_extract,
    run_ai_dev1_reconcile,
    run_calculation,
)


def _load_household_documents(household_id: str) -> list[dict]:
    document_paths = sorted(Path("organizer_pack/synthetic_documents/documents").glob(f"{household_id.lower()}*.pdf"))
    extracted_documents = []
    for pdf_path in document_paths:
        extracted_documents.append(
            run_ai_dev1_extract(
                pdf_path=pdf_path,
                document_id=pdf_path.stem,
                household_id=household_id,
                session_id="TEST-SESSION-001",
            )
        )
    return extracted_documents


@pytest.fixture()
def request_payload() -> dict:
    household_id = "HH-001"
    extracted_documents = _load_household_documents(household_id)
    reconciliation = run_ai_dev1_reconcile(extracted_documents)
    confirmed_profile = build_test_confirmed_profile(household_id=household_id, documents=extracted_documents)
    calculation = run_calculation(confirmed_profile)
    return build_ai_dev2_request(
        household_id=household_id,
        session_id="TEST-SESSION-001",
        extracted_documents=extracted_documents,
        reconciliation=reconciliation,
        confirmed_profile=confirmed_profile,
        calculation=calculation,
    )