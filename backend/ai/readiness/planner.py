from __future__ import annotations

from .schemas import NextStep, ReviewReason


def build_next_steps(reasons: list[ReviewReason]) -> list[NextStep]:
    steps: list[NextStep] = []
    seen: set[str] = set()

    for reason in reasons:
        action = reason.next_action
        if not action or action in seen:
            continue
        seen.add(action)
        steps.append(NextStep(
            order=len(steps) + 1,
            action=action,
            action_type="USER_REQUIRED",
        ))

    if steps:
        steps.append(NextStep(
            order=len(steps) + 1,
            action="Run the deterministic calculation and readiness checks again after corrections.",
            action_type="AUTOMATIC",
        ))
    return steps
