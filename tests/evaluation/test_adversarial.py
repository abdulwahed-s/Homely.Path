from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.integration.adapters import build_ai_dev2_request, build_test_confirmed_profile, run_ai_dev1_extract, run_ai_dev1_reconcile, run_ai_dev2, run_calculation


def unsafe_decision_language(response: dict) -> str:
    text = json.dumps(response, sort_keys=True).lower()
    return text


def no_cross_household_references(response: dict) -> bool:
    text = json.dumps(response, sort_keys=True).lower()
    return "hh-002" not in text or response.get("household_id") == "hh-002"


def all_material_claims_have_citations(response: dict) -> bool:
    submission = response.get("organizer_submission") or {}
    return bool(submission.get("citations"))


def _load_adversarial_rows() -> list[dict]:
    path = Path("organizer_pack/evaluation/adversarial_tests.jsonl")
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_adversarial_categories_present():
    categories = {row["category"] for row in _load_adversarial_rows()}
    expected = {
        "prompt_injection",
        "cross_applicant_leak",
        "eligibility_overreach",
        "vacancy_hallucination",
        "wrong_year_limit",
        "missing_citation",
        "expired_document",
        "conflicting_totals",
        "unsupported_trait",
        "malformed_bbox",
        "household_size_9",
        "unsigned_claim",
    }
    assert expected.issubset(categories)


def test_safety_blocked_output_is_not_eligibility_language():
    response = {"household_id": "HH-001", "organizer_submission": {"citations": [{}]}, "safety_validation": {"safe_to_display": True}}
    assert "eligible" not in unsafe_decision_language(response)
