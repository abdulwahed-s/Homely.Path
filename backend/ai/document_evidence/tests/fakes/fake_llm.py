"""Scripted fake :class:`VisionLLM` for tests (no network)."""

from typing import Dict, List, Optional, Union

from backend.ai.document_evidence.llm import LLMError

__all__ = ["FakeLLM"]


class FakeLLM:
    """Returns scripted JSON objects and records the calls it received.

    - Pass a single ``dict`` to always return (a copy of) it.
    - Pass a list of ``dict`` to return them in order (raises once exhausted).
    """

    def __init__(self, responses: Union[dict, List[dict], None] = None):
        if isinstance(responses, dict):
            self._single: Optional[dict] = responses
            self._queue: Optional[List[dict]] = None
        else:
            self._single = None
            self._queue = list(responses) if responses else []
        self.calls: List[tuple] = []
        self.last_messages: Optional[List[dict]] = None
        self.last_schema: Optional[dict] = None

    def complete_json(self, messages: List[dict], schema: dict) -> dict:
        self.last_messages = messages
        self.last_schema = schema
        self.calls.append((messages, schema))
        if self._single is not None:
            return dict(self._single)
        if self._queue:
            return dict(self._queue.pop(0))
        raise LLMError("FakeLLM has no scripted responses left")
