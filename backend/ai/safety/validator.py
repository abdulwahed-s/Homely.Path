from __future__ import annotations

from .policies import (
    ALLOWED_READINESS_STATUSES,
    CHAT_PROHIBITED_OUTPUT_PATTERNS,
    DECISION_ASSERTION_PATTERNS,
    MATERIAL_CLAIM_TERMS,
    PROTECTED_TRAITS,
    SCORE_OR_RANK_PATTERNS,
)
from .safe_responses import response_for
from .schemas import SafetyChecks, SafetyInput, SafetyStatus, SafetyValidation
from backend.ai.rules_chat.schemas import Citation


class SafetyValidator:
    def validate(self, payload: SafetyInput) -> SafetyValidation:
        combined = f"{payload.request_text}\n{payload.response_text}"
        response_lower = payload.response_text.lower()
        request_lower = payload.request_text.lower()

        decision = any(pattern.search(payload.response_text) for pattern in DECISION_ASSERTION_PATTERNS)
        scoring = any(pattern.search(combined) for pattern in SCORE_OR_RANK_PATTERNS)

        protected_request = any(term in request_lower for term in PROTECTED_TRAITS) and any(
            verb in request_lower for verb in ("infer", "guess", "determine", "identify")
        )
        protected_response = any(term in response_lower for term in PROTECTED_TRAITS) and any(
            phrase in response_lower for phrase in ("appears to be", "is likely", "must be", "is probably")
        )

        cross_household = False
        if payload.active_household_id:
            cross_household = any(
                household.upper() != payload.active_household_id.upper()
                for household in payload.referenced_household_ids
            )

        material_claim = any(term in response_lower for term in MATERIAL_CLAIM_TERMS)
        missing_citation = material_claim and not payload.citations

        non_deterministic = (
            payload.calculation_source is not None
            and payload.calculation_source != "deterministic"
        )

        invalid_readiness = (
            payload.readiness_status is not None
            and payload.readiness_status not in ALLOWED_READINESS_STATUSES
        )

        checks = SafetyChecks(
            decisioning_claim_present=decision,
            applicant_score_or_ranking_present=scoring,
            protected_trait_inference_present=protected_request or protected_response,
            cross_household_data_present=cross_household,
            missing_material_citation=missing_citation,
            non_deterministic_calculation_present=non_deterministic,
            unconfirmed_values_unlabelled=not payload.unconfirmed_values_labelled,
            invalid_readiness_status=invalid_readiness,
            property_availability_claim_present=payload.claims_current_property_availability,
        )

        violations: list[str] = []
        if checks.decisioning_claim_present:
            violations.append("ELIGIBILITY_DECISION")
        if checks.applicant_score_or_ranking_present:
            violations.append("APPLICANT_SCORING")
        if checks.protected_trait_inference_present:
            violations.append("PROTECTED_TRAIT_INFERENCE")
        if checks.cross_household_data_present:
            violations.append("CROSS_HOUSEHOLD_ACCESS")
        if checks.missing_material_citation:
            violations.append("MISSING_CITATION")
        if checks.non_deterministic_calculation_present:
            violations.append("NON_DETERMINISTIC_CALCULATION")
        if checks.unconfirmed_values_unlabelled:
            violations.append("UNCONFIRMED_VALUE")
        if checks.invalid_readiness_status:
            violations.append("INVALID_READINESS_STATUS")
        if checks.property_availability_claim_present:
            violations.append("PROPERTY_AVAILABILITY_CLAIM")

        if violations:
            return SafetyValidation(
                status=SafetyStatus.BLOCKED,
                safe_to_display=False,
                checks=checks,
                violations=violations,
                replacement_message=response_for(violations[0]),
            )

        return SafetyValidation(
            status=SafetyStatus.PASS,
            safe_to_display=True,
            checks=checks,
        )

    def validate_chat_answer(self, response: dict) -> SafetyValidation:
        """Final deterministic validation for a template-generated chat answer."""
        citations = [
            Citation(
                rule_id=item.get("rule_id"),
                effective_date=item.get("effective_date"),
            )
            for item in response.get("citations", [])
            if item.get("rule_id")
        ]
        validation_citations = (
            citations
            if response.get("status") == "SUPPORTED"
            else [Citation(rule_id="SAFE-RESPONSE")]
        )
        validation = self.validate(
            SafetyInput(
                response_text=(
                    f"{response.get('answer', '')}\n"
                    f"{response.get('disclaimer', '')}"
                ),
                citations=validation_citations,
                unconfirmed_values_labelled=True,
            )
        )
        answer = str(response.get("answer", ""))
        prohibited = any(
            pattern.search(answer)
            for pattern in CHAT_PROHIBITED_OUTPUT_PATTERNS
        )
        if not prohibited:
            return validation

        checks = validation.checks.model_copy(
            update={"property_availability_claim_present": True}
        )
        return SafetyValidation(
            status=SafetyStatus.BLOCKED,
            safe_to_display=False,
            checks=checks,
            violations=[
                *validation.violations,
                "PROPERTY_AVAILABILITY_CLAIM",
            ],
            replacement_message=response_for(
                "PROPERTY_AVAILABILITY_CLAIM"
            ),
        )
