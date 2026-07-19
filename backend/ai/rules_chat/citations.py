from __future__ import annotations

from .rule_store import RuleStore
from .schemas import Citation, QuestionIntent, RuleAnswer, RuleRecord


REQUIRED_RULES: dict[QuestionIntent, set[str]] = {
    QuestionIntent.THRESHOLD: {"HUD-MTSP-002"},
    QuestionIntent.ANNUALIZED_INCOME: {"CH-INCOME-001"},
    QuestionIntent.COMPARISON: {"HUD-MTSP-002", "CH-INCOME-001"},
    QuestionIntent.READINESS: {"CH-READINESS-001"},
    QuestionIntent.EFFECTIVE_DATE: {"HUD-MTSP-001"},
    QuestionIntent.DOCUMENT_FRESHNESS: {"CH-READINESS-001"},
    QuestionIntent.ELIGIBILITY_REQUEST: {"CH-DECISION-001"},
    QuestionIntent.PROPERTY_AVAILABILITY: {"HUD-DATA-001"},
    QuestionIntent.GEOCODE_QUALITY: {"HUD-GEO-001"},
    QuestionIntent.PROMPT_INJECTION: {"CH-SAFETY-001"},
    QuestionIntent.FEDERAL_ANCHOR: {"FED-LIHTC-001"},
    QuestionIntent.CROSS_HOUSEHOLD: {"CH-SAFETY-001"},
}


def citation_from_rule(rule: RuleRecord) -> Citation:
    return Citation(
        rule_id=rule.rule_id,
        authority=rule.authority,
        effective_date=rule.effective_date,
        source_url=rule.source_url,
        source_locator=rule.source_locator,
    )


def validate_rule_answer(answer: RuleAnswer, store: RuleStore) -> list[str]:
    errors: list[str] = []
    rule_citations = [citation for citation in answer.citations if citation.rule_id]
    cited_ids = {citation.rule_id for citation in rule_citations}

    if answer.status.value == "SUPPORTED" and not answer.citations:
        errors.append("Supported answers require citations")

    for citation in rule_citations:
        assert citation.rule_id is not None
        if citation.rule_id not in store:
            errors.append(f"Unknown cited rule: {citation.rule_id}")
            continue
        source = store.get(citation.rule_id)
        if citation.effective_date != source.effective_date:
            errors.append(f"Effective date mismatch for {citation.rule_id}")
        if citation.source_locator != source.source_locator:
            errors.append(f"Source locator mismatch for {citation.rule_id}")

    required = REQUIRED_RULES.get(answer.intent, set())
    missing = required - cited_ids
    if missing:
        errors.append(f"Missing required rule citations: {sorted(missing)}")

    return errors
