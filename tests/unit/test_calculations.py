from __future__ import annotations

from backend.calculations.annualization import annualize, compare_to_threshold
from backend.calculations.mtsp_lookup import lookup_threshold
from backend.calculations.service import calculate_household


def test_annualize_weekly():
    assert annualize(1000, "weekly") == 52000


def test_compare_to_threshold_boundary():
    assert compare_to_threshold(72000, 72000) == "below_or_equal"


def test_lookup_threshold_matches_table():
    assert lookup_threshold(1) == 72000.0


def test_calculate_household_happy_path():
    result = calculate_household(
        {
            "household_id": "HH-001",
            "household_size": 1,
            "values": [
                {"field": "gross_pay", "value": 2166.0, "source_document_id": "HH-001-D02", "document_type": "pay_stub", "source_page": 1, "source_bbox": [1, 1, 2, 2], "source_bbox_units": "pdf_points"},
                {"field": "pay_frequency", "value": "biweekly", "source_document_id": "HH-001-D02", "document_type": "pay_stub", "source_page": 1, "source_bbox": [1, 1, 2, 2], "source_bbox_units": "pdf_points"},
            ],
        }
    )

    assert result["annualized_income"] == 56316.0
    assert result["comparison"] == "below_or_equal"