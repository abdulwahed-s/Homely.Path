from __future__ import annotations

import re

# These patterns detect an asserted decision, not a refusal containing the word
# "eligibility". This avoids blocking safe sentences such as
# "I cannot determine eligibility."
DECISION_ASSERTION_PATTERNS = (
    re.compile(r"\b(?:you|the applicant|the household|hh-\d{3})\s+(?:is|are|will be|has been)\s+(?:eligible|ineligible|approved|denied|accepted|rejected)\b", re.I),
    re.compile(r"\b(?:approve|deny|accept|reject)\s+(?:this|the)\s+application\b", re.I),
)

SCORE_OR_RANK_PATTERNS = (
    re.compile(r"\bapplicant score\b", re.I),
    re.compile(r"\brank(?:ing)?\s+(?:the\s+)?applicants?\b", re.I),
    re.compile(r"\bapproval probability\b", re.I),
    re.compile(r"\bchance of approval\b", re.I),
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
