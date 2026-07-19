from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate


def validate_organizer_submission(result: dict[str, Any], schema_path: str | Path | None = None) -> None:
    path = Path(schema_path or "organizer_pack/starter/schemas/submission.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    validate(instance=result["organizer_submission"], schema=schema)