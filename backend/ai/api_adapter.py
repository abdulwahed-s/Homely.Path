from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from backend.ai.orchestration.service import AI2Service
from backend.ai.readiness.schemas import ReadinessInput
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
    if os.getenv("REALDOOR_PACK_ROOT"):
        candidates.append(Path(os.environ["REALDOOR_PACK_ROOT"]))
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

    result_json = result.model_dump(mode="json", exclude_none=True)
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
