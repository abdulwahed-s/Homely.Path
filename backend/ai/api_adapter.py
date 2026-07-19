from __future__ import annotations

import json
import os
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from backend.ai.orchestration.service import AI2Service
from backend.ai.readiness.schemas import CalculationResult, Conflict, OrganizerDocument, ReadinessInput
from backend.ai.readiness.service import ReadinessService
from backend.ai.rules_chat.rule_store import RuleStore
from backend.ai.rules_chat.schemas import ChatContext, ChatRequest
from backend.ai.rules_chat.service import RulesChatService
from backend.ai.safety.schemas import SafetyInput
from backend.ai.safety.validator import SafetyValidator


def resolve_pack_root(pack_root: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if pack_root is not None:
        candidates.append(Path(pack_root))
    # REALDOOR_PACK_ROOT (Dev 2) and REALDOOR_ORGANIZER_PACK (Dev 1) are aliases
    # for the same organizer pack; either one may be set on the deploy target.
    for env_name in ("REALDOOR_PACK_ROOT", "REALDOOR_ORGANIZER_PACK"):
        if os.getenv(env_name):
            candidates.append(Path(os.environ[env_name]))
    candidates.extend([
        Path("organizer_pack"),
        Path("realdoor-hackathon-starter-pack"),
    ])

    for candidate in candidates:
        if (candidate / "rules" / "rule_corpus.jsonl").is_file():
            return candidate.resolve()
        nested = candidate / "realdoor-hackathon-starter-pack"
        if (nested / "rules" / "rule_corpus.jsonl").is_file():
            return nested.resolve()

    raise FileNotFoundError(
        "Could not find the organizer pack. Set REALDOOR_PACK_ROOT or pass pack_root."
    )


def create_service(pack_root: str | Path | None = None) -> AI2Service:
    root = resolve_pack_root(pack_root)
    store = RuleStore.from_jsonl(root / "rules" / "rule_corpus.jsonl")
    return AI2Service(
        rules_chat=RulesChatService(store),
        readiness=ReadinessService(),
        safety=SafetyValidator(),
    )


def answer_question(
    request_payload: dict[str, Any],
    context_payload: dict[str, Any],
    pack_root: str | Path | None = None,
) -> dict[str, Any]:
    service = create_service(pack_root)
    answer, safety, provenance, event = service.answer_question(
        ChatRequest.model_validate(request_payload),
        ChatContext.model_validate(context_payload),
    )
    return {
        "answer": answer.model_dump(mode="json", exclude_none=True),
        "safety": safety.model_dump(mode="json", exclude_none=True),
        "provenance": provenance,
        "activity_event": event.model_dump(mode="json"),
    }


def evaluate_readiness(
    payload: dict[str, Any],
    pack_root: str | Path | None = None,
) -> dict[str, Any]:
    root = resolve_pack_root(pack_root)
    service = create_service(root)
    result, safety, provenance, event = service.evaluate_readiness(
        ReadinessInput.model_validate(payload)
    )

    result_json = _jsonable(result.model_dump(exclude_none=True))
    validate_against_submission_schema(result_json, root)
    return {
        "result": result_json,
        "safety": safety.model_dump(mode="json", exclude_none=True),
        "provenance": provenance,
        "activity_event": event.model_dump(mode="json"),
    }


def validate_output(payload: dict[str, Any], pack_root: str | Path | None = None) -> dict[str, Any]:
    service = create_service(pack_root)
    result = service.validate_output(SafetyInput.model_validate(payload))
    return result.model_dump(mode="json", exclude_none=True)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _to_organizer_document(document: dict[str, Any]) -> OrganizerDocument:
    return OrganizerDocument.model_validate(document)


def _to_conflict(conflict: dict[str, Any]) -> Conflict:
    return Conflict.model_validate({
        "conflict_id": conflict["conflict_id"],
        "conflict_type": conflict.get("conflict_type") or conflict.get("code"),
        "status": conflict.get("status", "UNRESOLVED"),
        "evidence_ids": conflict.get("evidence_ids", conflict.get("document_ids", [])),
        "reason": conflict.get("reason") or conflict.get("message"),
    })


def _to_calculation_result(payload: dict[str, Any]) -> CalculationResult:
    filtered = {
        key: value
        for key, value in payload.items()
        if key in {
            "household_id",
            "household_size",
            "annualized_income",
            "threshold",
            "comparison",
            "formula_steps",
            "calculation_source",
            "rule_year",
            "citations",
        }
    }
    return CalculationResult.model_validate(filtered)


def evaluate_application(
    request_payload: dict[str, Any],
    pack_root: str | Path | None = None,
) -> dict[str, Any]:
    service = create_service(pack_root)
    household_id = request_payload.get("household_id")
    calculation_payload = request_payload.get("calculation_result") or {}

    if request_payload.get("consent_confirmed") is False or calculation_payload.get("calculation_status") != "CALCULATED":
        safety = service.validate_output(SafetyInput(
            request_text="evaluate_application",
            response_text="INCOMPLETE",
            active_household_id=household_id,
            referenced_household_ids=[household_id] if household_id else [],
            readiness_status="NEEDS_REVIEW",
            unconfirmed_values_labelled=True,
        ))
        return {
            "household_id": household_id,
            "readiness_status": "NEEDS_REVIEW",
            "safety_validation": safety.model_dump(mode="json", exclude_none=True),
            "organizer_submission": None,
            "activity_event": {
                "component": "AI2Service",
                "action": "APPLICATION_INCOMPLETE",
                "status": "ACTION_REQUIRED",
                "message": "The deterministic calculation inputs were incomplete.",
            },
        }

    readiness_input = ReadinessInput(
        session_id=request_payload["session_id"],
        household_id=household_id,
        documents=[_to_organizer_document(document) for document in request_payload.get("document_summaries", [])],
        calculation_result=_to_calculation_result(calculation_payload),
        conflicts=[_to_conflict(conflict) for conflict in request_payload.get("conflicts", [])],
        evidence_gaps=list(request_payload.get("upstream_evidence_gaps", [])),
        unconfirmed_used_fields=[
            f'{item.get("source_document_id", "")}:{item.get("field", "")}'
            for item in request_payload.get("confirmed_profile", {}).get("values", [])
            if not item.get("confirmed_by_user", False)
        ],
        material_citations_valid=bool(calculation_payload.get("citations")),
    )

    result, safety, provenance, event = service.evaluate_readiness(readiness_input)
    result_json = _jsonable(result.model_dump(exclude_none=True))
    validate_against_submission_schema(result_json, pack_root)
    return {
        "household_id": household_id,
        "readiness_status": result_json["readiness_status"],
        "safety_validation": safety.model_dump(mode="json", exclude_none=True),
        "organizer_submission": result_json,
        "provenance": provenance,
        "activity_event": event.model_dump(mode="json"),
    }


def validate_against_submission_schema(
    result_payload: dict[str, Any],
    pack_root: str | Path | None = None,
) -> None:
    root = resolve_pack_root(pack_root)
    schema_path = root / "starter" / "schemas" / "submission.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    # The organizer schema allows extra UI fields, so validation directly checks
    # the required canonical fields without conversion.
    Draft202012Validator(schema).validate(result_payload)
