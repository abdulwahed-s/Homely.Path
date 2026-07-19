"""B3: injectable vision/LLM port.

A single, narrow boundary for model calls that return JSON. The Document
Evidence Agent depends on the :class:`VisionLLM` protocol, not a concrete
provider, so tests inject a fake and the live client can be added later.

This module contains no prompt text (prompts live in ``prompts.py``) and makes
no network call by default: :class:`DefaultVisionLLM` is a deferred boundary
(E2) that raises :class:`LLMError` until a real integration is provided.
"""

import json
from typing import Any, List, Optional, Protocol, runtime_checkable

__all__ = ["VisionLLM", "DefaultVisionLLM", "LLMError", "parse_json_response"]


class LLMError(Exception):
    """Raised when the model boundary fails or returns unusable output."""


@runtime_checkable
class VisionLLM(Protocol):
    """Model port: turn prompt messages into a JSON object."""

    def complete_json(self, messages: List[dict], schema: dict) -> dict:  # pragma: no cover
        ...


def parse_json_response(raw: Any) -> dict:
    """Parse a raw model text response into a JSON object.

    Raises :class:`LLMError` if the text is not valid JSON or is not a JSON
    object. Used by concrete :class:`VisionLLM` implementations.
    """
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise LLMError(f"model did not return valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("model JSON response must be an object")
    return data


class DefaultVisionLLM:
    """Real provider boundary. Live integration is deferred (E2).

    Constructed with model configuration so wiring is stable, but
    :meth:`complete_json` raises :class:`LLMError` until a live client is added.
    Callers inject a working :class:`VisionLLM` (real or fake) in the meantime.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def complete_json(self, messages: List[dict], schema: dict) -> dict:
        raise LLMError(
            "live vision model is deferred (E2); inject a VisionLLM implementation"
        )
