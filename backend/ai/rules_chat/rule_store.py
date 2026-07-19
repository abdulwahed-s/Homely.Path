from __future__ import annotations

import json
from pathlib import Path

from .schemas import RuleRecord


class RuleStore:
    """Loads only the organizer's frozen `rule_corpus.jsonl`."""

    def __init__(self, rules: dict[str, RuleRecord]):
        if not rules:
            raise ValueError("Rule corpus is empty")
        self._rules = rules

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "RuleStore":
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Frozen rule corpus not found: {path}")

        rows: dict[str, RuleRecord] = {}
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                rule = RuleRecord.model_validate(raw)
                if rule.rule_id in rows:
                    raise ValueError(f"Duplicate rule_id {rule.rule_id!r} on line {line_number}")
                rows[rule.rule_id] = rule
        return cls(rows)

    def get(self, rule_id: str) -> RuleRecord:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise KeyError(f"Unknown frozen rule_id: {rule_id}") from exc

    def get_many(self, rule_ids: list[str] | tuple[str, ...]) -> list[RuleRecord]:
        return [self.get(rule_id) for rule_id in rule_ids]

    def all(self) -> list[RuleRecord]:
        return list(self._rules.values())

    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._rules

    def __len__(self) -> int:
        return len(self._rules)
