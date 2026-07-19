"""Concrete OpenAI vision implementation of the :class:`VisionLLM` port.

Kept separate from ``llm.py`` (the port) so the rest of the agent never imports
a provider SDK directly. Requires the ``openai`` package and an API key. The
model is multimodal: messages may embed image parts (see
``build_multimodal_messages``).
"""

from __future__ import annotations

import os
from typing import List, Optional

from backend.ai.document_evidence.llm import LLMError, parse_json_response

__all__ = ["OpenAIVisionLLM", "build_multimodal_messages", "DEFAULT_MODEL"]

DEFAULT_MODEL = os.environ.get("REALDOOR_VISION_MODEL", "gpt-4o-mini")


def build_multimodal_messages(text_messages: List[dict], image_data_uri: Optional[str]) -> List[dict]:
    """Return OpenAI-style messages, attaching an image to the user turn.

    ``text_messages`` are ``{"role", "content": str}`` dicts from ``prompts``.
    When ``image_data_uri`` is provided, the last user message's content is
    converted into a list of parts with the image appended.
    """
    if not image_data_uri:
        return [dict(m) for m in text_messages]

    messages = [dict(m) for m in text_messages]
    for message in reversed(messages):
        if message.get("role") == "user":
            message["content"] = [
                {"type": "text", "text": message["content"]},
                {"type": "image_url", "image_url": {"url": image_data_uri}},
            ]
            break
    return messages


class OpenAIVisionLLM:
    """VisionLLM backed by the OpenAI Chat Completions API (JSON mode)."""

    def __init__(self, model: Optional[str] = None, client=None, api_key: Optional[str] = None):
        self.model = model or DEFAULT_MODEL
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise LLMError("openai package is not installed") from exc
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=key)

    def complete_json(self, messages: List[dict], schema: dict) -> dict:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001 - normalize any SDK error
            raise LLMError(f"vision model call failed: {exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:
            raise LLMError("vision model returned an unexpected response shape") from exc

        return parse_json_response(content)
