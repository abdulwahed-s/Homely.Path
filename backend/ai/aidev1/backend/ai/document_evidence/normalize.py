"""A2: deterministic string -> typed value normalization.

Pure and dependency-light (only the allowlist for field routing; no I/O, no
contract types). Converts raw extracted strings into the typed values used by
downstream calculation and reconciliation, matching the organizer gold types.

Design notes / gold-type parity
--------------------------------
The organizer gold file uses a per-field numeric convention that this module
reproduces exactly:

- Always-float money fields: ``hourly_rate``, ``gross_pay``, ``net_pay``,
  ``platform_fees`` (gold stores e.g. ``2166.0``, ``120.0``).
- "Number" fields that are integral in gold but may legitimately be fractional
  in perturbed inputs: ``regular_hours``, ``weekly_hours``, ``monthly_benefit``,
  ``gross_receipts`` -> returned as ``int`` when integral, else ``float``.
- Strict count: ``household_size`` -> ``int`` (never fractional).
- Dates -> ISO ``YYYY-MM-DD``; month -> ``YYYY-MM``; frequency -> canonical
  token; names/addresses -> trimmed strings.

Guarantees
----------
- No function raises on bad input; unparseable values return ``None``.
- No arithmetic / annualization (that belongs to the full-stack developer).
- ``untrusted_instruction_text`` is security-only and never yields a value.
"""

import math
from datetime import datetime
from typing import Optional, Tuple, Union

from backend.ai.document_evidence.allowlist import SECURITY_ONLY_FIELDS

__all__ = [
    "FREQUENCY_TOKENS",
    "normalize_money",
    "normalize_int",
    "normalize_float",
    "normalize_date",
    "normalize_month",
    "normalize_frequency",
    "normalize_field",
    "supported_fields",
]

Number = Union[int, float]

FREQUENCY_TOKENS = frozenset(
    {"weekly", "biweekly", "semimonthly", "monthly", "annual"}
)

# Raw frequency spellings -> canonical token. Keys are matched after lowercasing
# and removing spaces, hyphens, and underscores.
_FREQUENCY_ALIASES = {
    "weekly": "weekly",
    "everyweek": "weekly",
    "perweek": "weekly",
    "biweekly": "biweekly",
    "fortnightly": "biweekly",
    "everytwoweeks": "biweekly",
    "every2weeks": "biweekly",
    "semimonthly": "semimonthly",
    "twicemonthly": "semimonthly",
    "twiceamonth": "semimonthly",
    "monthly": "monthly",
    "permonth": "monthly",
    "everymonth": "monthly",
    "annual": "annual",
    "annually": "annual",
    "yearly": "annual",
    "peryear": "annual",
    "perannum": "annual",
}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y/%m/%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)

_MONTH_FORMATS = (
    "%Y-%m",
    "%m/%Y",
    "%B %Y",
    "%b %Y",
)

# Field-name -> normalization kind. Covers every allowlisted field name.
_FIELD_KIND = {
    # text
    "person_name": "text",
    "address": "text",
    # dates
    "application_date": "date",
    "pay_date": "date",
    "pay_period_start": "date",
    "pay_period_end": "date",
    "document_date": "date",
    # month
    "statement_month": "month",
    # frequency
    "pay_frequency": "frequency",
    "benefit_frequency": "frequency",
    # strict count
    "household_size": "count",
    # integral-or-float numbers (gold ints, but tolerate fractional)
    "regular_hours": "number",
    "weekly_hours": "number",
    "monthly_benefit": "number",
    "gross_receipts": "number",
    # always-float money
    "hourly_rate": "money",
    "gross_pay": "money",
    "net_pay": "money",
    "platform_fees": "money",
}


def _clean_numeric_string(raw) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("$", "").replace(" ", "")
    return s or None


def normalize_money(raw) -> Optional[float]:
    """Parse a currency string into a float. Returns ``None`` on failure."""
    s = _clean_numeric_string(raw)
    if s is None:
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def normalize_float(raw) -> Optional[float]:
    """Parse a numeric string into a float. Returns ``None`` on failure."""
    return normalize_money(raw)


def normalize_int(raw) -> Optional[int]:
    """Parse a strict integer (no fractional part). Returns ``None`` otherwise."""
    value = normalize_money(raw)
    if value is None:
        return None
    if value != int(value):
        return None
    return int(value)


def _normalize_number(raw) -> Optional[Number]:
    """Return ``int`` when the value is integral, otherwise ``float``."""
    value = normalize_money(raw)
    if value is None:
        return None
    if value == int(value):
        return int(value)
    return value


def normalize_date(raw) -> Optional[str]:
    """Parse a date into ISO ``YYYY-MM-DD``. Returns ``None`` on failure."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_month(raw) -> Optional[str]:
    """Parse a month into ISO ``YYYY-MM``. Returns ``None`` on failure."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    for fmt in _MONTH_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    full = normalize_date(s)
    if full:
        return full[:7]
    return None


def normalize_frequency(raw) -> Optional[str]:
    """Map a frequency spelling to a canonical token in :data:`FREQUENCY_TOKENS`."""
    if raw is None:
        return None
    key = str(raw).strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if not key:
        return None
    return _FREQUENCY_ALIASES.get(key)


def supported_fields() -> frozenset:
    """Return the set of field names this module knows how to normalize."""
    return frozenset(_FIELD_KIND)


def normalize_field(
    field_name: str, raw
) -> Tuple[Optional[str], Optional[Union[float, int, str]]]:
    """Normalize a raw value for a named field.

    Returns ``(display_value, normalized_value)`` where ``display_value`` is the
    trimmed original string (or ``None`` if empty/absent) for the contract
    ``ExtractedField.value``, and ``normalized_value`` is the typed value for
    ``ExtractedField.normalized_value`` (or ``None`` if unparseable).

    Security-only fields (e.g. ``untrusted_instruction_text``) never yield a
    value: they return ``(None, None)``.
    """
    if field_name in SECURITY_ONLY_FIELDS:
        return (None, None)

    display: Optional[str]
    if raw is None:
        display = None
    else:
        display = str(raw).strip() or None

    kind = _FIELD_KIND.get(field_name, "text")
    if kind == "text":
        normalized: Optional[Union[float, int, str]] = display
    elif kind == "date":
        normalized = normalize_date(raw)
    elif kind == "month":
        normalized = normalize_month(raw)
    elif kind == "frequency":
        normalized = normalize_frequency(raw)
    elif kind == "count":
        normalized = normalize_int(raw)
    elif kind == "number":
        normalized = _normalize_number(raw)
    elif kind == "money":
        normalized = normalize_money(raw)
    else:  # pragma: no cover - defensive; all kinds handled above
        normalized = display

    return (display, normalized)
