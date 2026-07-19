from __future__ import annotations

from .rule_store import RuleStore
from .schemas import QuestionIntent, RuleRecord


INTENT_RULE_IDS: dict[QuestionIntent, tuple[str, ...]] = {
    QuestionIntent.THRESHOLD: ("HUD-MTSP-002",),
    QuestionIntent.ANNUALIZED_INCOME: ("CH-INCOME-001",),
    QuestionIntent.COMPARISON: ("HUD-MTSP-002", "CH-INCOME-001"),
    QuestionIntent.READINESS: ("CH-READINESS-001",),
    QuestionIntent.EFFECTIVE_DATE: ("HUD-MTSP-001",),
    QuestionIntent.DOCUMENT_FRESHNESS: ("CH-READINESS-001",),
    QuestionIntent.ELIGIBILITY_REQUEST: ("CH-DECISION-001",),
    QuestionIntent.PROPERTY_AVAILABILITY: ("HUD-DATA-001",),
    QuestionIntent.GEOCODE_QUALITY: ("HUD-GEO-001",),
    QuestionIntent.PROMPT_INJECTION: ("CH-SAFETY-001",),
    QuestionIntent.FEDERAL_ANCHOR: ("FED-LIHTC-001",),
    QuestionIntent.CROSS_HOUSEHOLD: ("CH-SAFETY-001",),
    QuestionIntent.UNSUPPORTED_TRAIT: ("CH-INCOME-001", "CH-DECISION-001"),
    QuestionIntent.UNSUPPORTED: (),
}


def retrieve_rules(intent: QuestionIntent, store: RuleStore) -> list[RuleRecord]:
    return store.get_many(INTENT_RULE_IDS[intent])
