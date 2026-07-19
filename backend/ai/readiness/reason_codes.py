from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReasonCode(StrEnum):
    PAY_STUB_TOTAL_CONFLICT = "PAY_STUB_TOTAL_CONFLICT"
    GIG_INCOME_UNCORROBORATED = "GIG_INCOME_UNCORROBORATED"
    EMPLOYMENT_LETTER_EXPIRED = "EMPLOYMENT_LETTER_EXPIRED"
    UNCONFIRMED_REQUIRED_FIELD = "UNCONFIRMED_REQUIRED_FIELD"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    MISSING_CITATION = "MISSING_CITATION"
    NO_FROZEN_THRESHOLD = "NO_FROZEN_THRESHOLD"
    UNVERIFIED_SELF_DECLARATION = "UNVERIFIED_SELF_DECLARATION"
    UNSUPPORTED_INCOME_FREQUENCY = "UNSUPPORTED_INCOME_FREQUENCY"
    MISSING_REQUIRED_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"


@dataclass(frozen=True)
class ReasonDefinition:
    message: str
    next_action: str
    blocks_readiness: bool = True


REASON_DEFINITIONS: dict[str, ReasonDefinition] = {
    ReasonCode.PAY_STUB_TOTAL_CONFLICT: ReasonDefinition(
        "Pay components and the displayed gross total do not reconcile.",
        "Review the highlighted pay values and confirm the correct recurring gross amount.",
    ),
    ReasonCode.GIG_INCOME_UNCORROBORATED: ReasonDefinition(
        "The gig-income amount does not have sufficient corroborating evidence.",
        "Add corroborating evidence or ask a human reviewer how the program documents gig income.",
    ),
    ReasonCode.EMPLOYMENT_LETTER_EXPIRED: ReasonDefinition(
        "The employment letter is older than the simulation's 60-day current-evidence window.",
        "Provide a current employment letter or request human review of acceptable alternatives.",
    ),
    ReasonCode.UNCONFIRMED_REQUIRED_FIELD: ReasonDefinition(
        "A value used in the calculation has not been confirmed by the renter.",
        "Review and confirm every value used in the deterministic calculation.",
    ),
    ReasonCode.UNRESOLVED_CONFLICT: ReasonDefinition(
        "The submitted evidence contains an unresolved conflict.",
        "Review the conflicting evidence and resolve or explain the difference.",
    ),
    ReasonCode.MISSING_CITATION: ReasonDefinition(
        "A material result is not traceable to the required document or rule citation.",
        "Restore the missing page/source-box or rule citation before review.",
    ),
    ReasonCode.NO_FROZEN_THRESHOLD: ReasonDefinition(
        "The supplied frozen table does not contain a threshold for this household size.",
        "Route the case to a human reviewer instead of extending the table.",
    ),
    ReasonCode.UNVERIFIED_SELF_DECLARATION: ReasonDefinition(
        "A self-declared amount is being used without independent supporting evidence.",
        "Provide supporting evidence or keep the amount out of the calculation.",
    ),
    ReasonCode.UNSUPPORTED_INCOME_FREQUENCY: ReasonDefinition(
        "The income frequency is not supported by the frozen deterministic calculation rules.",
        "Confirm a supported frequency before recalculating.",
    ),
    ReasonCode.MISSING_REQUIRED_EVIDENCE: ReasonDefinition(
        "Required evidence for a material income source is missing.",
        "Add the missing evidence or request human review of an acceptable alternative.",
    ),
}


def reason_definition(code: str) -> ReasonDefinition:
    return REASON_DEFINITIONS.get(
        code,
        ReasonDefinition(
            "The evidence requires human review.",
            "Review the cited evidence and resolve the outstanding issue.",
        ),
    )
