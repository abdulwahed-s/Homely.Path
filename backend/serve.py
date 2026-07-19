"""Run the AI Developer 1 HTTP service.

    python serve.py                 # http://127.0.0.1:8000
    python serve.py --port 9000

Routes:
    GET  /health
    POST /internal/ai/extract     (multipart: document_id, session_id, file=<pdf>)
    POST /internal/ai/reconcile   (json: {"documents": [DocumentExtractionResult, ...]})

Uses the real OpenAI vision model (needs OPENAI_API_KEY, loaded from .env) and
OCR for rasterized pages.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.document_evidence.env_config import load_env  # noqa: E402

load_env()

logger = logging.getLogger("realdoor.aidev1")


def _warn_if_uncalibrated() -> None:
    """FR1.13 safety net: never run uncalibrated without saying so.

    On a fresh deploy the gold-fitted ``calibration_data.json`` is absent (it is
    gitignored), so confidence silently degrades to identity passthrough. Emit a
    loud WARNING so the deploy owner knows to run ``python calibrate.py --offline``.
    """
    from backend.ai.document_evidence import calibration

    if not calibration.get_active().has_learned_data():
        logger.warning(
            "CONFIDENCE IS UNCALIBRATED (identity passthrough): %s not found. "
            "Run `python calibrate.py --offline` (needs organizer_pack) before/at "
            "deploy to satisfy FR1.13. See INTEGRATION.md.",
            calibration.DATA_PATH,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve AI Developer 1 endpoints")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    _warn_if_uncalibrated()

    import uvicorn

    from backend.ai.api import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
