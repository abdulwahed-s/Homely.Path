from __future__ import annotations

from .evaluator import evaluate_readiness
from .planner import build_next_steps
from .schemas import ReadinessInput, ReadinessResult


class ReadinessService:
    """Deterministic readiness evaluator; no LLM decides the status."""

    def evaluate(self, data: ReadinessInput) -> ReadinessResult:
        result = evaluate_readiness(data)
        result.next_steps = build_next_steps(result.review_reasons)
        return result
