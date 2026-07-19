from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.ai.readiness.schemas import CalculationResult
from backend.ai.rules_chat.citations import citation_from_rule
from backend.ai.rules_chat.rule_store import RuleStore
from backend.ai.rules_chat.schemas import Citation

from .annualization import annualize, compare_to_threshold
from .mtsp_lookup import lookup_row, lookup_threshold, resolve_pack_root


def _value_text(item: dict[str, Any]) -> Any:
    return item.get("value")


def _group_values(values: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = OrderedDict()
    for item in values:
        source_document_id = item.get("source_document_id")
        if not source_document_id:
            continue
        groups.setdefault(source_document_id, []).append(item)
    return groups


def _doc_type(items: list[dict[str, Any]]) -> str | None:
    for item in items:
        doc_type = item.get("document_type")
        if doc_type:
            return str(doc_type)
    return None


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _document_citation(item: dict[str, Any]) -> Citation | None:
    page = item.get("source_page")
    bbox = item.get("source_bbox")
    if not item.get("source_document_id") or page is None or bbox is None:
        return None
    return Citation(
        document_id=item["source_document_id"],
        page=int(page),
        bbox=tuple(float(value) for value in bbox),
        bbox_units=item.get("source_bbox_units", "pdf_points"),
    )


def _rule_citations(pack_root: str | Path | None = None) -> list[Citation]:
    root = resolve_pack_root(pack_root)
    store = RuleStore.from_jsonl(root / "rules" / "rule_corpus.jsonl")
    ordered_ids = ["CH-INCOME-001", "HUD-MTSP-002"]
    return [citation_from_rule(store.get(rule_id)) for rule_id in ordered_ids if rule_id in store]


def calculate_household(
    confirmed_profile: dict[str, Any],
    pack_root: str | Path | None = None,
) -> dict[str, Any]:
    household_id = str(confirmed_profile.get("household_id", ""))
    household_size = confirmed_profile.get("household_size")
    values = list(confirmed_profile.get("values", []))
    groups = _group_values(values)

    formula_steps: list[dict[str, Any]] = []
    citations: list[Citation] = []
    annualized_income = 0.0
    used_fields: list[str] = []
    calculation_status = "CALCULATED"

    for source_document_id, items in groups.items():
        doc_type = _doc_type(items)
        if doc_type == "pay_stub":
            gross_pay = _numeric(next((item.get("value") for item in items if item.get("field") == "gross_pay"), None))
            pay_frequency = next((item.get("value") for item in items if item.get("field") == "pay_frequency"), None)
            if gross_pay is None or pay_frequency is None:
                calculation_status = "NOT_CALCULATED"
                continue
            contribution = annualize(gross_pay, str(pay_frequency))
            formula = f"{gross_pay} x {pay_frequency}"
        elif doc_type == "employment_letter":
            weekly_hours = _numeric(next((item.get("value") for item in items if item.get("field") == "weekly_hours"), None))
            hourly_rate = _numeric(next((item.get("value") for item in items if item.get("field") == "hourly_rate"), None))
            if weekly_hours is None or hourly_rate is None:
                calculation_status = "NOT_CALCULATED"
                continue
            contribution = round(float(weekly_hours) * float(hourly_rate) * 52, 2)
            formula = f"{weekly_hours} x {hourly_rate} x 52"
        elif doc_type == "benefit_letter":
            monthly_benefit = _numeric(next((item.get("value") for item in items if item.get("field") == "monthly_benefit"), None))
            if monthly_benefit is None:
                calculation_status = "NOT_CALCULATED"
                continue
            contribution = round(float(monthly_benefit) * 12, 2)
            formula = f"{monthly_benefit} x 12"
        elif doc_type == "gig_statement":
            gross_receipts = _numeric(next((item.get("value") for item in items if item.get("field") == "gross_receipts"), None))
            if gross_receipts is None:
                calculation_status = "NOT_CALCULATED"
                continue
            contribution = round(float(gross_receipts) * 12, 2)
            formula = f"{gross_receipts} x 12"
        else:
            continue

        annualized_income = round(annualized_income + contribution, 2)
        used_fields.extend(item.get("field", "") for item in items if item.get("field"))
        formula_steps.append({
            "label": f"{source_document_id}:{doc_type}",
            "formula": formula,
            "result": contribution,
        })

        citation = next((c for c in (_document_citation(item) for item in items) if c is not None), None)
        if citation is not None:
            citations.append(citation)

    threshold = lookup_threshold(int(household_size), pack_root) if household_size is not None else None
    comparison = (
        compare_to_threshold(annualized_income, threshold)
        if threshold is not None and calculation_status == "CALCULATED"
        else "no_frozen_threshold"
    )

    citations.extend(_rule_citations(pack_root))

    if calculation_status == "NOT_CALCULATED":
        annualized_value = None
        comparison = "no_frozen_threshold"
    else:
        annualized_value = annualized_income

    result = CalculationResult(
        household_id=household_id,
        household_size=int(household_size) if household_size is not None else 1,
        annualized_income=Decimal(str(annualized_value)) if annualized_value is not None else Decimal("0"),
        threshold=Decimal(str(threshold)) if threshold is not None else None,
        comparison=comparison,
        formula_steps=[
            {
                "label": step["label"],
                "formula": step["formula"],
                "result": Decimal(str(step["result"])),
            }
            for step in formula_steps
        ],
        citations=citations,
    )

    payload = {
        "household_id": result.household_id,
        "household_size": result.household_size,
        "annualized_income": float(result.annualized_income),
        "threshold": float(result.threshold) if result.threshold is not None else None,
        "comparison": result.comparison,
        "formula_steps": [
            {
                "label": step.label,
                "formula": step.formula,
                "result": float(step.result),
            }
            for step in result.formula_steps
        ],
        "calculation_source": result.calculation_source,
        "rule_year": result.rule_year,
        "citations": [citation.model_dump(mode="json", exclude_none=True) for citation in citations],
        "calculation_status": calculation_status,
        "used_fields": used_fields,
    }
    if threshold is not None:
        payload["threshold_source"] = lookup_row(int(household_size), pack_root)
    return payload