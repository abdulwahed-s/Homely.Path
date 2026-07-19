import pytest

from backend.discovery.safety import (
    assert_public_property,
    assert_safe_response_text,
    forbidden_query_fields,
)


def test_protected_traits_income_and_scores_cannot_be_filters():
    rejected = forbidden_query_fields(
        ["state", "race", "renter_income", "applicant_score", "bedrooms"]
    )

    assert rejected == ["applicant_score", "race", "renter_income"]


def test_private_profile_data_cannot_enter_discovery():
    with pytest.raises(ValueError, match="confirmed_profile"):
        assert_public_property(
            {"property_id": "MA-1", "confirmed_profile": {"income": 1}}
        )


@pytest.mark.parametrize(
    "text",
    [
        "Best match",
        "Recommended for you",
        "Likely to accept",
        "High approval chance",
        "You qualify",
        "Top property",
    ],
)
def test_decisional_labels_are_rejected(text):
    with pytest.raises(ValueError):
        assert_safe_response_text(text)
