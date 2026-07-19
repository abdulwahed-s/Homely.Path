"""Minimal ``.env`` loader (no third-party dependency).

Reads ``aidev1/.env`` and populates ``os.environ`` for keys that are not
already set, so ``OPENAI_API_KEY`` / ``REALDOOR_VISION_MODEL`` are available to
the OpenAI adapter. Existing environment variables always win.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

__all__ = ["load_env", "find_env", "find_organizer_pack"]

# aidev1 root is four parents up: document_evidence -> ai -> backend -> aidev1
_AIDEV1_ROOT = Path(__file__).resolve().parents[3]


def find_organizer_pack(start: Optional[Path] = None) -> Optional[Path]:
    """Locate the canonical ``organizer_pack`` directory.

    Resolution order (so callers never hardcode a duplicate):
    1. ``REALDOOR_ORGANIZER_PACK`` env var, if it points at a directory.
    2. The nearest ``organizer_pack`` found by walking up from ``start`` (or the
       aidev1 root) toward the project root — this picks up a canonical copy
       placed at ``C:\\Homely.Path\\organizer_pack`` if/when one exists.
    Returns ``None`` if no pack is found.
    """
    override = os.environ.get("REALDOOR_ORGANIZER_PACK")
    if override and Path(override).is_dir():
        return Path(override)
    base = Path(start) if start else _AIDEV1_ROOT
    for directory in [base, *base.parents]:
        candidate = directory / "organizer_pack"
        if candidate.is_dir():
            return candidate
    return None


def find_env(start: Optional[Path] = None) -> Optional[Path]:
    """Return the path to ``.env`` at the aidev1 root, if it exists."""
    candidate = (start or _AIDEV1_ROOT) / ".env"
    return candidate if candidate.is_file() else None


def load_env(path: Optional[Path] = None, override: bool = False) -> bool:
    """Load ``.env`` into ``os.environ``. Returns True if a file was read.

    Lines are ``KEY=VALUE``; blank lines and ``#`` comments are ignored. Values
    may be optionally quoted. Existing env vars are preserved unless
    ``override`` is True.
    """
    env_path = path or find_env()
    if env_path is None or not env_path.is_file():
        return False

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
    return True
