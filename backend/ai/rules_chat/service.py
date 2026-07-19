from __future__ import annotations

from decimal import Decimal

from .citations import citation_from_rule, validate_rule_answer
from .intent_router import classify_intent
from .retriever import retrieve_rules
from .rule_store import RuleStore
from .schemas import (
    AnswerStatus,
    ChatContext,
    ChatRequest,
    Citation,
    QuestionIntent,
    RuleAnswer,
)


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
