from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# These patterns detect an asserted decision, not a refusal containing the word
# "eligibility". This avoids blocking safe sentences such as
# "I cannot determine eligibility."
DECISION_ASSERTION_PATTERNS = (
    re.compile(r"(?<!whether )\b(?:you|the applicant|the household|hh-\d{3})\s+(?:is|are|will be|has been)\s+(?:eligible|ineligible|approved|denied|accepted|rejected)\b", re.I),
    re.compile(r"\b(?:approve|deny|accept|reject)\s+(?:this|the)\s+application\b", re.I),
)

SCORE_OR_RANK_PATTERNS = (
    re.compile(r"\bapplicant score\b", re.I),
    re.compile(r"\brank(?:ing)?\s+(?:the\s+)?applicants?\b", re.I),
    re.compile(r"\bapproval probability\b", re.I),
    re.compile(r"\bchance of approval\b", re.I),
)

CHAT_PROHIBITED_OUTPUT_PATTERNS = (
    re.compile(r"\b(?:this|the) propert(?:y|ies)\s+(?:is|are)\s+(?:currently )?available\b", re.I),
    re.compile(r"\b(?:this|the) (?:building|property)\s+has\s+(?:a |an )?(?:vacancy|open unit)\b", re.I),
    re.compile(r"\bbest propert(?:y|ies) for you\b", re.I),
    re.compile(r"\bmost likely to accept you\b", re.I),
)

PROTECTED_TRAITS = (
    "race", "ethnicity", "religion", "disability", "disabled",
    "immigration status", "sexual orientation", "health condition",
)

MATERIAL_CLAIM_TERMS = (
    "$", "threshold", "annualized income", "annual income", "below_or_equal",
    "above", "ready_to_review", "needs_review", "effective date",
)

ALLOWED_READINESS_STATUSES = {"READY_TO_REVIEW", "NEEDS_REVIEW"}


class SensitiveCategory(StrEnum):
    ELIGIBILITY = "ELIGIBILITY"
    APPROVAL = "APPROVAL"
    ACCEPTANCE = "ACCEPTANCE"
    RANKING = "RANKING"
    AVAILABILITY = "AVAILABILITY"
    PROTECTED_TRAIT = "PROTECTED_TRAIT"
    CROSS_HOUSEHOLD = "CROSS_HOUSEHOLD"
    PROMPT_OVERRIDE = "PROMPT_OVERRIDE"


@dataclass(frozen=True)
class SensitiveMatch:
    blocked: bool
    category: SensitiveCategory | None = None


BLOCKED_PATTERNS: dict[SensitiveCategory, tuple[str, ...]] = {
    SensitiveCategory.ELIGIBILITY: (
        r"\bam i eligible\b",
        r"\bdo i qualify\b",
        r"\bqualif(?:y|ied) for\b",
        r"\beligib(?:le|ility) for\b",
    ),
    SensitiveCategory.APPROVAL: (
        r"\bwill i be approv(?:ed|al)\b",
        r"\bwill (?:i|my application) be denied\b",
        r"\bapproval chances?\b",
        r"\bprobability of approval\b",
        r"\bchance of (?:being )?approved\b",
    ),
    SensitiveCategory.ACCEPTANCE: (
        r"\bwhich propert(?:y|ies) (?:will|would|might) accept me\b",
        r"\bwill .* accept me\b",
        r"\blikely to accept\b",
        r"\bacceptance probability\b",
        r"\bchance of acceptance\b",
        r"\bmost likely to be accepted\b",
    ),
    SensitiveCategory.RANKING: (
        r"\brank .* propert",
        r"\bbest (?:property|housing|apartment).*(?:for me)?\b",
        r"\btop match\b",
        r"\brecommended for me\b",
    ),
    SensitiveCategory.AVAILABILITY: (
        r"\b(?:is|are) .* (?:currently |now )?available\b",
        r"\bopen units?\b",
        r"\bcurrently vacant\b",
        r"\bopen waitlist\b",
        r"\bwaitlist open\b",
        r"\bhas vacancies\b",
    ),
    SensitiveCategory.PROTECTED_TRAIT: (
        r"\brace\b",
        r"\breligion\b",
        r"\bethnicity\b",
        r"\bdisabilit(?:y|ies)\b",
        r"\bsexual orientation\b",
        r"\bnational(?:ity| origin)\b",
        r"\bpregnan",
        r"\bpeople like me\b",
    ),
    SensitiveCategory.CROSS_HOUSEHOLD: (
        r"\bother applicants?\b",
        r"\bother households?\b",
        r"\banother renters?\b",
        r"\bcompare me with\b",
        r"\bshow me hh-\d+\b",
        r"\bhh-\d+'s\b",
    ),
    SensitiveCategory.PROMPT_OVERRIDE: (
        r"\bignore .* rules\b",
        r"\bignore .* instructions\b",
        r"\bpretend you are\b",
        r"\bdo not include .* disclaimer\b",
        r"\breveal hidden\b",
        r"\boverride .* safety\b",
    ),
}


def detect_sensitive_question(question: str) -> SensitiveMatch:
    """Run deterministic prohibited-question checks before any retrieval."""
    normalized = " ".join(question.casefold().split())
    for category, patterns in BLOCKED_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return SensitiveMatch(blocked=True, category=category)
    return SensitiveMatch(blocked=False)
