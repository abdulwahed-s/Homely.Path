"""Allowlist: the single source of truth for the scored extraction surface.

Step A1. This module is intentionally dependency-free (no contract imports, no
I/O) and fully deterministic. It answers two questions:

1. Which fields may be extracted for a given document type? (``fields_for``)
2. Is a given ``(document_type, field_name)`` pair a scored profile field?
   (``is_allowed``)

The field lists in :data:`ALLOWLIST` are derived from, and must stay in sync
with, the organizer gold file
``organizer_pack/synthetic_documents/gold/document_gold.jsonl``. A gold-parity
test guards this invariant.

``untrusted_instruction_text`` appears inside several gold records but is a
*security signal only* (see ``aidev1.txt``). It is never a profile field and is
listed in :data:`SECURITY_ONLY_FIELDS` so downstream code can treat it
explicitly rather than by omission.

Note on types: :class:`contracts.extraction_contract.DocumentType` is a
``str`` subclass, so enum members work directly as keys here; ``fields_for`` and
``is_allowed`` also normalize any object exposing a ``.value`` attribute.
"""

from typing import List

__all__ = [
    "ALLOWLIST",
    "SECURITY_ONLY_FIELDS",
    "fields_for",
    "is_allowed",
]


# Ordered scored-field surface per document type. Order is significant and is
# preserved by ``fields_for``. Kept identical to the organizer gold field sets.
ALLOWLIST = {
    "application_summary": [
        "person_name",
        "household_size",
        "address",
        "application_date",
    ],
    "pay_stub": [
        "person_name",
        "pay_date",
        "pay_period_start",
        "pay_period_end",
        "pay_frequency",
        "regular_hours",
        "hourly_rate",
        "gross_pay",
        "net_pay",
    ],
    "employment_letter": [
        "person_name",
        "document_date",
        "weekly_hours",
        "hourly_rate",
    ],
    "benefit_letter": [
        "person_name",
        "document_date",
        "monthly_benefit",
        "benefit_frequency",
    ],
    "gig_statement": [
        "person_name",
        "statement_month",
        "gross_receipts",
        "platform_fees",
    ],
}


# Fields that may appear in gold records but are security signals, never scored
# profile fields. Downstream extraction MUST NOT surface these as values.
SECURITY_ONLY_FIELDS = frozenset({"untrusted_instruction_text"})


def _normalize_type(document_type) -> object:
    """Return a plain-string-comparable key for ``document_type``.

    Accepts a raw ``str`` or any enum-like object exposing ``.value`` (e.g.
    :class:`DocumentType`). ``None`` and unknown values pass through unchanged
    and simply miss the :data:`ALLOWLIST` lookup.
    """
    return getattr(document_type, "value", document_type)


def fields_for(document_type: str) -> List[str]:
    """Return the ordered list of allowlisted field names for a document type.

    Args:
        document_type: A document-type string or :class:`DocumentType` member.

    Returns:
        A new list (safe to mutate) of allowlisted field names in canonical
        order. Unknown, ``None``, or unsupported types yield an empty list.
    """
    key = _normalize_type(document_type)
    return list(ALLOWLIST.get(key, ()))


def is_allowed(document_type: str, field_name: str) -> bool:
    """Return whether ``field_name`` is a scored profile field for the type.

    Security-only fields (:data:`SECURITY_ONLY_FIELDS`) always return ``False``,
    as do unknown types, unknown fields, and ``None`` inputs.
    """
    if field_name in SECURITY_ONLY_FIELDS:
        return False
    key = _normalize_type(document_type)
    return field_name in ALLOWLIST.get(key, ())
