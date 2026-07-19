from __future__ import annotations

import re

from .schemas import QuestionIntent

_HOUSEHOLD_PATTERN = re.compile(r"\bHH-\d{3}\b", re.IGNORECASE)

_PROTECTED_TRAITS = (
    "race", "ethnicity", "religion", "disability", "disabled",
    "immigration status", "sexual orientation", "health condition",
)


def referenced_households(text: str) -> set[str]:
    return {value.upper() for value in _HOUSEHOLD_PATTERN.findall(text)}


def classify_intent(question: str, active_household_id: str | None = None) -> QuestionIntent:
    text = " ".join(question.lower().split())
    households = referenced_households(question)

    # Safety and privacy checks always run before ordinary routing.
    if active_household_id and any(hh != active_household_id.upper() for hh in households):
        return QuestionIntent.CROSS_HOUSEHOLD

    if any(term in text for term in _PROTECTED_TRAITS) and any(
        verb in text for verb in ("infer", "guess", "determine", "identify", "tell me")
    ):
        return QuestionIntent.UNSUPPORTED_TRAIT

    if any(term in text for term in (
        "eligible", "ineligible", "approved", "denied", "approve", "deny",
        "acceptance chance", "chance of approval", "prioritize", "rank applicant",
    )):
        return QuestionIntent.ELIGIBILITY_REQUEST

    if any(term in text for term in ("vacant", "vacancy", "available today", "unit available", "waitlist")):
        return QuestionIntent.PROPERTY_AVAILABILITY

    if "geocode" in text or "address display" in text:
        return QuestionIntent.GEOCODE_QUALITY

    if any(term in text for term in ("embedded instruction", "inside a pay stub", "prompt injection", "ignore system")):
        return QuestionIntent.PROMPT_INJECTION

    if "federal statutory" in text or "statutory anchor" in text or "26 u.s.c" in text:
        return QuestionIntent.FEDERAL_ANCHOR

    if "effective" in text or "take effect" in text:
        return QuestionIntent.EFFECTIVE_DATE

    if "60-day" in text or "60 day" in text or "current document" in text or "expired" in text:
        return QuestionIntent.DOCUMENT_FRESHNESS

    if "threshold" in text or "60%" in text or "60 percent" in text:
        return QuestionIntent.THRESHOLD

    if "annualized income" in text or "annual income" in text or "annualize" in text:
        return QuestionIntent.ANNUALIZED_INCOME

    if "compare" in text or "comparison" in text or "below_or_equal" in text:
        return QuestionIntent.COMPARISON

    if "readiness" in text or "ready_to_review" in text or "needs_review" in text:
        return QuestionIntent.READINESS

    return QuestionIntent.UNSUPPORTED
