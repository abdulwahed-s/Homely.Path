from __future__ import annotations

from backend.ai.readiness.schemas import ReadinessInput, ReadinessResult
from backend.ai.readiness.service import ReadinessService
from backend.ai.rules_chat.intent_router import referenced_households
from backend.ai.rules_chat.schemas import (
    AnswerStatus,
    ChatContext,
    ChatRequest,
    RuleAnswer,
)
from backend.ai.rules_chat.service import RulesChatService
from backend.ai.safety.schemas import SafetyInput, SafetyValidation
from backend.ai.safety.validator import SafetyValidator

from .activity import ActivityEvent, ActivityStatus, make_activity_event
from .provenance import build_answer_provenance, build_readiness_provenance


class AI2Service:
    """Small integration facade used by the full-stack developer."""

    def __init__(
        self,
        rules_chat: RulesChatService,
        readiness: ReadinessService | None = None,
        safety: SafetyValidator | None = None,
    ):
        self.rules_chat = rules_chat
        self.readiness = readiness or ReadinessService()
        self.safety = safety or SafetyValidator()

    def answer_question(
        self,
        request: ChatRequest,
        context: ChatContext,
    ) -> tuple[RuleAnswer, SafetyValidation, dict, ActivityEvent]:
        answer = self.rules_chat.answer(request, context)
        safety = self.safety.validate(SafetyInput(
            request_text=request.question,
            response_text=answer.answer or "",
            citations=answer.citations,
            active_household_id=context.active_household_id,
            referenced_household_ids=sorted(referenced_households(request.question)),
            calculation_source=(
                context.calculation.calculation_source
                if context.calculation is not None
                else None
            ),
            readiness_status=context.readiness_status,
            unconfirmed_values_labelled=True,
            claims_current_property_availability=False,
        ))

        if not safety.safe_to_display:
            answer = RuleAnswer(
                status=AnswerStatus.REFUSED,
                intent=answer.intent,
                answer=safety.replacement_message,
                citations=answer.citations,
                reasons=safety.violations,
                requires_human_review=True,
            )

        event = make_activity_event(
            component="RulesChatService",
            action="ANSWER_VALIDATED",
            status=(ActivityStatus.PASS if safety.safe_to_display else ActivityStatus.ACTION_REQUIRED),
            message=(
                "The grounded answer passed final safety validation."
                if safety.safe_to_display
                else "The generated answer was replaced by a safe response."
            ),
        )
        return answer, safety, build_answer_provenance(answer), event

    def evaluate_readiness(
        self,
        data: ReadinessInput,
    ) -> tuple[ReadinessResult, SafetyValidation, dict, ActivityEvent]:
        result = self.readiness.evaluate(data)
        safety = self.safety.validate(SafetyInput(
            response_text=(
                f"{result.readiness_status.value}; "
                + "; ".join(reason.message for reason in result.review_reasons)
            ),
            citations=result.citations,
            active_household_id=data.household_id,
            referenced_household_ids=[data.household_id],
            calculation_source=data.calculation_result.calculation_source,
            readiness_status=result.readiness_status.value,
            unconfirmed_values_labelled=True,  # Evaluator explicitly labels these in review reasons/checklist.
        ))

        event = make_activity_event(
            component="ReadinessService",
            action="READINESS_EVALUATED",
            status=(
                ActivityStatus.PASS
                if result.readiness_status.value == "READY_TO_REVIEW" and safety.safe_to_display
                else ActivityStatus.ACTION_REQUIRED
            ),
            message=(
                "The packet is ready for human review."
                if result.readiness_status.value == "READY_TO_REVIEW"
                else "The packet contains items that require review."
            ),
        )
        return result, safety, build_readiness_provenance(result), event

    def validate_output(self, payload: SafetyInput) -> SafetyValidation:
        return self.safety.validate(payload)
