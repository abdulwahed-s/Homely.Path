from __future__ import annotations

from typing import Any

from .document_summary_builder import build_document_summaries


def build_evaluation_request(
    *,
    household_id: str,
    session_id: str,
    extracted_documents: list[dict[str, Any]],
    reconciliation: dict[str, Any],
    confirmed_profile: dict[str, Any],
    calculation: dict[str, Any],
    document_summaries: list[dict[str, Any]] | None = None,
    upstream_evidence_gaps: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "request_id": f"REQ-{household_id}",
        "session_id": session_id,
        "household_id": household_id,
        "consent_confirmed": True,
        "reference_date": "2026-07-18",
        "document_summaries": document_summaries or build_document_summaries(extracted_documents),
        "confirmed_profile": confirmed_profile,
        "conflicts": reconciliation.get("conflicts", []),
        "upstream_evidence_gaps": upstream_evidence_gaps or [],
        "calculation_result": calculation,
    }