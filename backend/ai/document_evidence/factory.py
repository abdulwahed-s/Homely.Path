"""Factory helpers for selecting a :class:`VisionLLM` implementation."""

from __future__ import annotations

import os
from typing import Optional

from backend.ai.document_evidence.env_config import load_env
from backend.ai.document_evidence.llm_openai import OpenAIVisionLLM

__all__ = ["has_openai_key", "build_vision_llm"]


def has_openai_key() -> bool:
    load_env()
    return bool(os.environ.get("OPENAI_API_KEY"))


def build_vision_llm(model: Optional[str] = None) -> OpenAIVisionLLM:
    """Build the real OpenAI-backed vision model (requires OPENAI_API_KEY).

    Loads ``aidev1/.env`` first so the key and ``REALDOOR_VISION_MODEL`` are
    picked up without extra shell setup.
    """
    load_env()
    model = model or os.environ.get("REALDOOR_VISION_MODEL")
    return OpenAIVisionLLM(model=model)
