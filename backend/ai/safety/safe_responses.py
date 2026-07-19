from backend.ai.safety.policies import SensitiveCategory


SAFE_RESPONSES: dict[str, str] = {
    "ELIGIBILITY_DECISION": (
        "I cannot determine eligibility, approval or denial. I can show the "
        "confirmed inputs, frozen rule, deterministic calculation and readiness "
        "items that require human review."
    ),
    "APPLICANT_SCORING": (
        "I cannot score, rank or prioritize applicants. I can only prepare and "
        "explain this household's evidence for human review."
    ),
    "PROTECTED_TRAIT_INFERENCE": (
        "I cannot infer or use protected or sensitive characteristics. I can "
        "only use documented, allowlisted application information."
    ),
    "CROSS_HOUSEHOLD_ACCESS": (
        "I cannot access or disclose another household's documents or profile information."
    ),
    "MISSING_CITATION": (
        "I cannot display this material result because its required evidence or rule citation is missing."
    ),
    "NON_DETERMINISTIC_CALCULATION": (
        "I cannot display an AI-generated income calculation. Run the organizer-aligned deterministic calculation service."
    ),
    "INVALID_READINESS_STATUS": (
        "The result must use only READY_TO_REVIEW or NEEDS_REVIEW."
    ),
    "PROPERTY_AVAILABILITY_CLAIM": (
        "The HUD property dataset does not confirm current vacancies, rents, waitlists or application status."
    ),
    "UNCONFIRMED_VALUE": (
        "A value has not been confirmed by the renter and must be clearly labelled before display."
    ),
}


SAFE_REFUSALS: dict[SensitiveCategory, str] = {
    SensitiveCategory.ELIGIBILITY: (
        "I cannot determine whether you are eligible or qualify. I can explain "
        "the confirmed income calculation, applicable threshold, readiness "
        "status, and documents needing review."
    ),
    SensitiveCategory.APPROVAL: (
        "I cannot predict approval or denial. I can explain which parts of the "
        "application are ready and which need review."
    ),
    SensitiveCategory.ACCEPTANCE: (
        "I cannot predict whether a property or housing provider will accept an "
        "application."
    ),
    SensitiveCategory.RANKING: (
        "I cannot rank properties by acceptance likelihood or applicant "
        "characteristics. Properties may only be ordered using filters selected "
        "by the renter."
    ),
    SensitiveCategory.AVAILABILITY: (
        "Current availability is unknown unless supplied by a separate verified "
        "source. The public property dataset does not establish current vacancies "
        "or open waitlists."
    ),
    SensitiveCategory.PROTECTED_TRAIT: (
        "I cannot use protected traits or demographic proxies to recommend, "
        "filter, rank, or predict housing outcomes."
    ),
    SensitiveCategory.CROSS_HOUSEHOLD: (
        "I cannot access or disclose information from another household or "
        "applicant."
    ),
    SensitiveCategory.PROMPT_OVERRIDE: (
        "I cannot ignore the application-safety and privacy rules. I can answer "
        "supported questions about the current household's readiness results and "
        "frozen rules."
    ),
}


def response_for(violation: str) -> str:
    return SAFE_RESPONSES.get(
        violation,
        "This output requires human review before it can be displayed.",
    )
