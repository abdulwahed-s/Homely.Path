"""Offline gold-backed fake :class:`VisionLLM` for end-to-end runs without a key.

Constructed with a single document's gold record. It inspects the prompt to
decide whether it is being asked to classify or to extract, and returns the
gold answer. This exercises the *real* pipeline (PDF loading, box location,
normalization, confidence, injection scan, reconciliation) deterministically
and at zero cost — the only thing faked is the model's reading of the page.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__all__ = ["GoldBackedLLM"]

# Fields that are security signals, never returned as extracted values.
_SECURITY_FIELDS = {"untrusted_instruction_text"}


class GoldBackedLLM:
    def __init__(self, gold_record: Optional[Dict[str, Any]] = None):
        self._gold = gold_record or {}
        self.last_messages: Optional[List[dict]] = None

    def _system_text(self, messages: List[dict]) -> str:
        for message in messages:
            if message.get("role") == "system":
                content = message.get("content", "")
                if isinstance(content, str):
                    return content.lower()
        return ""

    def complete_json(self, messages: List[dict], schema: dict) -> dict:
        self.last_messages = messages
        system = self._system_text(messages)

        if "classify" in system:
            return {
                "document_type": self._gold.get("document_type", "unknown"),
                "confidence": 0.95,
            }

        # Extraction: return gold field values keyed by field name.
        out: Dict[str, Any] = {}
        for field in self._gold.get("fields", []):
            name = field.get("field")
            if not name or name in _SECURITY_FIELDS:
                continue
            out[name] = field.get("value")
        return out
