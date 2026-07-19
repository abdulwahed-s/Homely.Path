from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from tests.integration.adapters import build_ai_dev2_request


def validate_organizer_submission(result: dict) -> None:
    schema_path = Path("organizer_pack/starter/schemas/submission.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=result["organizer_submission"], schema=schema)


def test_household_ids_match(request_payload):
    expected = request_payload["household_id"]

    assert request_payload["confirmed_profile"]["household_id"] == expected
    assert request_payload["calculation_result"]["household_id"] == expected

    for document in request_payload["document_summaries"]:
        assert document["household_id"] == expected


def test_calculation_is_deterministic(request_payload):
    assert request_payload["calculation_result"]["calculation_source"] == "deterministic"


def test_confirmed_inputs(request_payload):
    for item in request_payload["confirmed_profile"]["values"]:
        assert item["confirmed_by_user"] is True


def test_document_boxes(request_payload):
    for conflict in request_payload["conflicts"]:
        for evidence in conflict["observed_values"]:
            assert evidence["page"] >= 1
            assert len(evidence["bbox"]) == 4
            assert evidence["bbox_units"] == "pdf_points"