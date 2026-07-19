"""Configuration constants for the Document Evidence Agent (A-phase).

Centralizes tunable thresholds so behaviour can be adjusted without editing
logic. Kept as plain module constants (no I/O, no env reads) for deterministic,
merge-safe defaults during the hackathon.
"""

# --- Organizer page geometry (PDF points, bottom-left origin) ---------------
EXPECTED_PAGE_SIZE = (612.0, 792.0)

# --- Confidence tiering thresholds (A5) -------------------------------------
# score >= HIGH -> HIGH; score >= MEDIUM -> MEDIUM; otherwise LOW.
CONFIDENCE_HIGH_THRESHOLD = 0.80
CONFIDENCE_MEDIUM_THRESHOLD = 0.50

# --- Confidence signal penalties / caps (A5) --------------------------------
# OCR-derived values are multiplied down relative to native text extraction.
CONFIDENCE_OCR_FACTOR = 0.90
# A value adjacent to detected injection text can never be rated HIGH.
CONFIDENCE_INJECTION_MAX = 0.75
# Without a valid source box a value has no provenance -> forced LOW.
CONFIDENCE_NO_BOX_MAX = 0.40
# A value that failed to normalize is unreliable -> forced LOW.
CONFIDENCE_NO_PARSE_MAX = 0.30
# A box located by the vision model itself (no text layer / OCR) has weaker
# provenance than a text/OCR match, so it is capped at MEDIUM. This is the
# no-OCR path for rasterized pages: the value is real (model-read) but the box
# is approximate, so it is prefilled yet flagged for careful review.
CONFIDENCE_MODEL_BOX_MAX = 0.70
