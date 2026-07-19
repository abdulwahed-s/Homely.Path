from __future__ import annotations

from decimal import Decimal

from .citations import citation_from_rule, validate_rule_answer
from .intent_router import (
    GroundedChatIntent,
    classify_intent,
    route_grounded_intent,
)
from .retriever import retrieve_rules
from .rule_store import RuleStore
from .schemas import (
    AnswerStatus,
    ChatContext,
    ChatRequest,
    Citation,
    GroundedChatContext,
    GroundedChatResponse,
    GroundedChatStatus,
    QuestionIntent,
    ResultReference,
    RuleCitation,
    RuleAnswer,
)
from backend.ai.safety.policies import detect_sensitive_question
from backend.ai.safety.safe_responses import SAFE_REFUSALS


def _currency(value: Decimal, decimals: bool = False) -> str:
    return f"${value:,.2f}" if decimals else f"${value:,.0f}"


class RulesChatService:
    def __init__(self, store: RuleStore):
        self.store = store

    def answer(self, request: ChatRequest, context: ChatContext) -> RuleAnswer:
        if request.session_id != context.session_id:
            return self._refuse(
                QuestionIntent.CROSS_HOUSEHOLD,
                "The request does not belong to the active session.",
            )

        intent = classify_intent(request.question, context.active_household_id)
        rules = retrieve_rules(intent, self.store)
        rule_citations = [citation_from_rule(rule) for rule in rules]

        if intent == QuestionIntent.CROSS_HOUSEHOLD:
            return self._refuse(
                intent,
                "I cannot access or disclose another household's documents or profile information.",
                rule_citations,
            )

        if intent == QuestionIntent.UNSUPPORTED_TRAIT:
            return self._refuse(
                intent,
                "I cannot infer or use protected or sensitive characteristics. I can only use documented, allowlisted application information.",
                rule_citations,
            )

        if intent == QuestionIntent.ELIGIBILITY_REQUEST:
            return self._refuse(
                intent,
                "I cannot determine eligibility, approval or denial. I can report the confirmed inputs, frozen rule, numerical comparison and readiness status for human review.",
                rule_citations,
            )

        if intent == QuestionIntent.PROPERTY_AVAILABILITY:
            answer = RuleAnswer(
                status=AnswerStatus.SUPPORTED,
                intent=intent,
                answer="No. The HUD LIHTC data is a project inventory, not a current vacancy, rent, waitlist or application-status feed.",
                citations=rule_citations,
            )
            return self._checked(answer)

        if intent == QuestionIntent.GEOCODE_QUALITY:
            return self._checked(RuleAnswer(
                status=AnswerStatus.SUPPORTED,
                intent=intent,
                answer="HUD identifies geocode precision codes R and 4 as the higher-precision codes suitable for address display.",
                citations=rule_citations,
            ))

        if intent == QuestionIntent.PROMPT_INJECTION:
            return self._checked(RuleAnswer(
                status=AnswerStatus.SUPPORTED,
                intent=intent,
                answer="Treat instructions embedded inside uploaded documents as untrusted text and ignore them.",
                citations=rule_citations,
            ))

        if intent == QuestionIntent.EFFECTIVE_DATE:
            effective = rules[0].effective_date if rules else None
            answer_text = "The frozen FY 2026 MTSP limits take effect on May 1, 2026." if effective else None
            return self._checked(RuleAnswer(
                status=AnswerStatus.SUPPORTED if answer_text else AnswerStatus.ABSTAINED,
                intent=intent,
                answer=answer_text,
                citations=rule_citations,
                reasons=[] if answer_text else ["The frozen rule does not provide an effective date."],
            ))

        if intent == QuestionIntent.DOCUMENT_FRESHNESS:
            return self._checked(RuleAnswer(
                status=AnswerStatus.SUPPORTED,
                intent=intent,
                answer="For this hackathon simulation, evidence dated no more than 60 days before 2026-07-18 is treated as current. This is not a universal LIHTC rule.",
                citations=rule_citations,
            ))

        if intent == QuestionIntent.FEDERAL_ANCHOR:
            return self._checked(RuleAnswer(
                status=AnswerStatus.SUPPORTED,
                intent=intent,
                answer="The federal statutory anchor is 26 U.S.C. section 42.",
                citations=rule_citations,
            ))

        if intent in {
            QuestionIntent.THRESHOLD,
            QuestionIntent.ANNUALIZED_INCOME,
            QuestionIntent.COMPARISON,
            QuestionIntent.READINESS,
        }:
            return self._answer_from_context(intent, context, rule_citations)

        return RuleAnswer(
            status=AnswerStatus.ABSTAINED,
            intent=QuestionIntent.UNSUPPORTED,
            answer=None,
            reasons=["The frozen organizer corpus does not support this question."],
            next_action="Ask about the frozen threshold, annualized income, numerical comparison, readiness status or a listed rule.",
            requires_human_review=True,
        )

    def _answer_from_context(
        self,
        intent: QuestionIntent,
        context: ChatContext,
        rule_citations: list[Citation],
    ) -> RuleAnswer:
        calculation = context.calculation
        if calculation is None:
            return RuleAnswer(
                status=AnswerStatus.ABSTAINED,
                intent=intent,
                answer=None,
                citations=rule_citations,
                reasons=["No trusted deterministic calculation result is available."],
                next_action="Complete renter confirmation and run the deterministic calculation service.",
                requires_human_review=True,
            )

        if context.active_household_id and calculation.household_id != context.active_household_id:
            return self._refuse(
                QuestionIntent.CROSS_HOUSEHOLD,
                "The calculation result does not belong to the active household.",
                [citation_from_rule(self.store.get("CH-SAFETY-001"))],
            )

        document_citations = [c for c in calculation.citations if c.document_id]
        citations = [*rule_citations, *document_citations]

        if intent == QuestionIntent.THRESHOLD:
            if calculation.threshold is None:
                return self._abstain(intent, rule_citations, "No frozen threshold exists for this household size.")
            text = f"The frozen 60% threshold is {_currency(calculation.threshold)} for household size {calculation.household_size}."

        elif intent == QuestionIntent.ANNUALIZED_INCOME:
            if calculation.annualized_income is None:
                return self._abstain(intent, rule_citations, "The deterministic annualized income is not available.")
            text = f"The documented annualized income is {_currency(calculation.annualized_income, decimals=True)} under the frozen annualization convention."

        elif intent == QuestionIntent.COMPARISON:
            if calculation.comparison is None:
                return self._abstain(intent, rule_citations, "The deterministic comparison is not available.")
            text = calculation.comparison

        else:  # READINESS
            if context.readiness_status is None:
                return self._abstain(intent, rule_citations, "The readiness evaluation has not been completed.")
            text = context.readiness_status

        return self._checked(RuleAnswer(
            status=AnswerStatus.SUPPORTED,
            intent=intent,
            answer=text,
            citations=citations,
            requires_human_review=context.readiness_status == "NEEDS_REVIEW",
        ))

    def _checked(self, answer: RuleAnswer) -> RuleAnswer:
        errors = validate_rule_answer(answer, self.store)
        if errors:
            return RuleAnswer(
                status=AnswerStatus.ABSTAINED,
                intent=answer.intent,
                answer=None,
                citations=answer.citations,
                reasons=errors,
                next_action="Review the frozen-rule citation mapping.",
                requires_human_review=True,
            )
        return answer

    @staticmethod
    def _abstain(intent: QuestionIntent, citations: list[Citation], reason: str) -> RuleAnswer:
        return RuleAnswer(
            status=AnswerStatus.ABSTAINED,
            intent=intent,
            answer=None,
            citations=citations,
            reasons=[reason],
            next_action="Complete or correct the missing confirmed information.",
            requires_human_review=True,
        )

    @staticmethod
    def _refuse(
        intent: QuestionIntent,
        message: str,
        citations: list[Citation] | None = None,
    ) -> RuleAnswer:
        return RuleAnswer(
            status=AnswerStatus.REFUSED,
            intent=intent,
            answer=message,
            citations=citations or [],
            requires_human_review=True,
        )


RULE_TITLES = {
    "CH-INCOME-001": "Frozen income annualization convention",
    "CH-READINESS-001": "Readiness review rules",
    "HUD-MTSP-002": "FY 2026 MTSP income limits",
    "HUD-DATA-001": "HUD LIHTC public data limitations",
}


class GroundedRulesChatService:
    """Session-scoped, template-only Q&A with no model or raw-document access."""

    def __init__(self, *, rule_store: RuleStore, safety_validator) -> None:
        self.rule_store = rule_store
        self.safety_validator = safety_validator

    def answer(
        self,
        question: str,
        context: GroundedChatContext | None,
    ) -> GroundedChatResponse:
        # This must remain the first operation: no intent or context retrieval
        # may occur for a prohibited question.
        sensitive = detect_sensitive_question(question)
        if sensitive.blocked and sensitive.category is not None:
            return self._finalize(
                GroundedChatResponse(
                    status=GroundedChatStatus.REFUSED,
                    intent=sensitive.category.value,
                    answer=SAFE_REFUSALS[sensitive.category],
                )
            )

        if context is None:
            raise ValueError("A trusted chat context is required")

        intent = route_grounded_intent(question)
        handlers = {
            GroundedChatIntent.EXPLAIN_READINESS: self._readiness_answer,
            GroundedChatIntent.EXPLAIN_CALCULATION: self._calculation_answer,
            GroundedChatIntent.EXPLAIN_DOCUMENTS: self._documents_answer,
            GroundedChatIntent.EXPLAIN_NEXT_STEPS: self._next_steps_answer,
            GroundedChatIntent.EXPLAIN_MTSP: self._mtsp_answer,
            GroundedChatIntent.EXPLAIN_FMR: self._fmr_answer,
            GroundedChatIntent.EXPLAIN_DISCOVERY: self._discovery_answer,
        }
        handler = handlers.get(intent)
        response = (
            handler(context)
            if handler
            else GroundedChatResponse(
                status=GroundedChatStatus.ABSTAINED,
                intent=GroundedChatIntent.OUT_OF_SCOPE.value,
                answer=(
                    "I do not have enough supported information in the frozen "
                    "rules or your current results to answer that question."
                ),
            )
        )
        return self._finalize(response)

    def _readiness_answer(
        self, context: GroundedChatContext
    ) -> GroundedChatResponse:
        if not context.readiness_status:
            return self._abstain(
                GroundedChatIntent.EXPLAIN_READINESS,
                "A readiness result is not available yet.",
            )
        messages = [
            str(reason["message"])
            for reason in context.review_reasons
            if reason.get("message")
        ]
        references = [
            ResultReference(type="REVIEW_REASON", code=reason.get("code"))
            for reason in context.review_reasons
        ]
        references.extend(
            ResultReference(
                type="CONFLICT",
                code=conflict.get("code") or conflict.get("conflict_type"),
            )
            for conflict in context.conflicts
        )
        reason_text = (
            " ".join(messages)
            if messages
            else "No specific readiness issue is currently recorded."
        )
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_READINESS.value,
            answer=(
                f"Your current readiness status is {context.readiness_status}. "
                f"{reason_text}"
            ),
            citations=[self._citation("CH-READINESS-001")],
            result_references=references
            or [
                ResultReference(
                    type="READINESS_RESULT",
                    label="Current readiness result",
                )
            ],
        )

    def _calculation_answer(
        self, context: GroundedChatContext
    ) -> GroundedChatResponse:
        calculation = context.calculation
        if not calculation:
            return self._abstain(
                GroundedChatIntent.EXPLAIN_CALCULATION,
                "A deterministic calculation is not available.",
            )
        if calculation.get("calculation_source") != "deterministic":
            return self._abstain(
                GroundedChatIntent.EXPLAIN_CALCULATION,
                "A trusted deterministic calculation is not available.",
            )
        steps = calculation.get("formula_steps")
        if not isinstance(steps, list) or not steps:
            return self._abstain(
                GroundedChatIntent.EXPLAIN_CALCULATION,
                "The deterministic calculation steps are unavailable.",
            )
        descriptions = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            label = step.get("label", "Income source")
            formula = step.get("formula")
            result = step.get("result")
            if formula is not None and result is not None:
                descriptions.append(f"{label}: {formula} = ${float(result):,.2f}.")
        if not descriptions:
            return self._abstain(
                GroundedChatIntent.EXPLAIN_CALCULATION,
                "The deterministic calculation steps are unavailable.",
            )
        total = calculation.get("annualized_income")
        total_text = (
            f" The documented annualized total is ${float(total):,.2f}."
            if total is not None
            else ""
        )
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_CALCULATION.value,
            answer=(
                "The calculation used confirmed values and the frozen "
                "annualization convention. "
                + " ".join(descriptions)
                + total_text
            ),
            citations=[
                self._citation("CH-INCOME-001"),
                self._citation("HUD-MTSP-002"),
            ],
            result_references=[
                ResultReference(
                    type="CALCULATION",
                    label="Stored deterministic calculation",
                )
            ],
        )

    def _documents_answer(
        self, context: GroundedChatContext
    ) -> GroundedChatResponse:
        attention_statuses = {
            "MISSING",
            "EXPIRED",
            "UNCONFIRMED",
            "NEEDS_REVIEW",
        }
        issues = [
            item
            for item in context.checklist
            if str(item.get("status", "")).upper() in attention_statuses
        ]
        descriptions = [
            f"{item.get('item') or item.get('code') or 'Item'}: "
            f"{item.get('status')}"
            for item in issues
        ]
        descriptions.extend(
            str(conflict.get("message") or conflict.get("reason"))
            for conflict in context.conflicts
            if conflict.get("message") or conflict.get("reason")
        )
        answer = (
            "The following items need attention: "
            + "; ".join(descriptions)
            + "."
            if descriptions
            else (
                "The current checklist does not show a missing, expired, "
                "unconfirmed, conflicting, or needs-review document."
            )
        )
        references = [
            ResultReference(
                type="CHECKLIST_ITEM",
                code=item.get("code"),
                document_id=item.get("document_id"),
            )
            for item in issues
        ]
        references.extend(
            ResultReference(
                type="CONFLICT",
                code=conflict.get("code") or conflict.get("conflict_type"),
            )
            for conflict in context.conflicts
        )
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_DOCUMENTS.value,
            answer=answer,
            citations=[self._citation("CH-READINESS-001")],
            result_references=references,
        )

    def _next_steps_answer(
        self, context: GroundedChatContext
    ) -> GroundedChatResponse:
        steps = [
            str(step["action"])
            for step in context.next_steps
            if step.get("action")
        ]
        if not steps:
            return self._abstain(
                GroundedChatIntent.EXPLAIN_NEXT_STEPS,
                "No next steps are available yet.",
            )
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_NEXT_STEPS.value,
            answer="Next steps: " + "; ".join(steps) + ".",
            citations=[self._citation("CH-READINESS-001")],
            result_references=[
                ResultReference(type="NEXT_STEP", code=step.get("code"))
                for step in context.next_steps
                if step.get("action")
            ],
        )

    def _mtsp_answer(
        self, _context: GroundedChatContext
    ) -> GroundedChatResponse:
        if "HUD-MTSP-002" not in self.rule_store:
            return self._abstain(
                GroundedChatIntent.EXPLAIN_MTSP,
                "The frozen MTSP rule is unavailable.",
            )
        rule = self.rule_store.get("HUD-MTSP-002")
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_MTSP.value,
            answer=rule.text,
            citations=[self._citation(rule.rule_id)],
        )

    def _fmr_answer(
        self, context: GroundedChatContext
    ) -> GroundedChatResponse:
        selected = context.selected_property or {}
        reference = selected.get("fmr_reference")
        if not isinstance(reference, dict):
            return self._abstain(
                GroundedChatIntent.EXPLAIN_FMR,
                "A selected property's FMR reference is not available.",
            )
        label = reference.get(
            "label", "HUD area rent benchmark — not property rent."
        )
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_FMR.value,
            answer=(
                f"The selected property's structured result describes FMR as: "
                f"{label} It does not establish current availability."
            ),
            result_references=[
                ResultReference(
                    type="PROPERTY_FMR",
                    code=selected.get("property_id"),
                )
            ],
        )

    def _discovery_answer(
        self, _context: GroundedChatContext
    ) -> GroundedChatResponse:
        return GroundedChatResponse(
            status=GroundedChatStatus.SUPPORTED,
            intent=GroundedChatIntent.EXPLAIN_DISCOVERY.value,
            answer=(
                "The discovery list uses public property data. Availability "
                "remains unknown unless a separate verified source supplies "
                "current vacancy information. The list does not predict "
                "acceptance or eligibility."
            ),
            citations=[self._citation("HUD-DATA-001")],
        )

    def _citation(self, rule_id: str) -> RuleCitation:
        if rule_id not in self.rule_store:
            raise KeyError(f"Required frozen chat rule is missing: {rule_id}")
        rule = self.rule_store.get(rule_id)
        return RuleCitation(
            rule_id=rule.rule_id,
            title=RULE_TITLES.get(rule.rule_id),
            effective_date=rule.effective_date,
            source_label=f"{rule.authority}: {rule.source_locator}",
        )

    @staticmethod
    def _abstain(
        intent: GroundedChatIntent, message: str
    ) -> GroundedChatResponse:
        return GroundedChatResponse(
            status=GroundedChatStatus.ABSTAINED,
            intent=intent.value,
            answer=message + " I will not guess.",
        )

    def _finalize(
        self, response: GroundedChatResponse
    ) -> GroundedChatResponse:
        validation = self.safety_validator.validate_chat_answer(
            response.model_dump(mode="json")
        )
        if validation.safe_to_display:
            return response
        return GroundedChatResponse(
            status=GroundedChatStatus.REFUSED,
            intent="SAFETY_BLOCKED",
            answer=validation.replacement_message
            or "This answer requires human review.",
            safe_to_display=True,
        )
