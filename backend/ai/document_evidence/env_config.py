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
    # REALDOOR_ORGANIZER_PACK (Dev 1) and REALDOOR_PACK_ROOT (Dev 2) are aliases
    # for the same organizer pack; either one may be set on the deploy target.
    for env_name in ("REALDOOR_ORGANIZER_PACK", "REALDOOR_PACK_ROOT"):
        override = os.environ.get(env_name)
        if override and Path(override).is_dir():
            return Path(override)
    base = Path(start) if start else _AIDEV1_ROOT
    for directory in [base, *base.parents]:
        candidate = directory / "organizer_pack"
        if candidate.is_dir():
            return candidate
    return None


def _env_candidates(start: Optional[Path] = None) -> list[Path]:
    """Ordered ``.env`` locations to probe.

    ``env_config.py`` lives at ``backend/ai/document_evidence``, so the real
    ``.env`` (holding OPENAI_API_KEY) sits at ``backend/ai/aidev1/.env`` — a
    sibling, not a parent. Also probe the repo root and the current working
    directory so the loader works regardless of where the process is launched.
    """
    ai_dir = Path(__file__).resolve().parents[1]  # backend/ai
    repo_root = ai_dir.parents[1]                  # repo root
    candidates: list[Path] = []
    if start is not None:
        candidates.append(Path(start) / ".env")
    candidates.extend([
        ai_dir / "aidev1" / ".env",
        repo_root / ".env",
        Path.cwd() / ".env",
    ])
    # de-dup while preserving order
    seen: set[str] = set()
    unique: list[Path] = []
    for c in candidates:
        key = str(c.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def find_env(start: Optional[Path] = None) -> Optional[Path]:
    """Return the first existing ``.env`` among the candidate locations."""
    for candidate in _env_candidates(start):
        if candidate.is_file():
            return candidate
    return None


def load_env(path: Optional[Path] = None, override: bool = False) -> bool:
    """Load ``.env`` into ``os.environ``. Returns True if a file was read.

    Lines are ``KEY=VALUE``; blank lines and ``#`` comments are ignored. Values
    may be optionally quoted. Existing env vars are preserved unless
    ``override`` is True.
    """
    env_path = path or find_env()
    if env_path is None or not env_path.is_file():
        return False

    # utf-8-sig strips a leading BOM so the first key isn't read as
    # "\ufeffOPENAI_API_KEY" (a common cause of "key not set" on Windows editors).
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
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
