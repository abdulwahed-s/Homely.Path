"""Validated request and response models for property discovery."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DiscoverySort(StrEnum):
    ALPHABETICAL = "alphabetical"
    DISTANCE = "distance"


class DiscoveryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str = Field(min_length=2, max_length=2)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_miles: float | None = Field(default=None, gt=0, le=100)
    bedrooms: int | None = Field(default=None, ge=0, le=4)
    household_size: int | None = Field(default=None, ge=1, le=8)
    sort_by: DiscoverySort = DiscoverySort.ALPHABETICAL

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError("state must be a two-letter code")
        return value

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("city cannot be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_location(self) -> "DiscoveryQuery":
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude and longitude must be supplied together")
        if self.radius_miles is not None and not has_latitude:
            raise ValueError("radius_miles requires latitude and longitude")
        if self.sort_by == DiscoverySort.DISTANCE and not has_latitude:
            raise ValueError("distance sorting requires latitude and longitude")
        return self


class AppliedFilter(BaseModel):
    field: str
    value: str | int | float
    selected_by: Literal["RENTER"] = "RENTER"


class Ordering(BaseModel):
    method: DiscoverySort
    selected_by: Literal["RENTER"] = "RENTER"


class Availability(BaseModel):
    status: Literal["UNKNOWN"] = "UNKNOWN"
    message: str = "Current availability is not included in the public dataset."


class FmrReference(BaseModel):
    fiscal_year: int
    bedrooms: int
    amount: float | None
    label: str = "HUD area rent benchmark — not property rent."


class MtspReference(BaseModel):
    fiscal_year: int
    household_size: int
    income_limit: float | None
    label: str = (
        "HUD area income-limit reference — not an eligibility or acceptance decision."
    )


class DiscoveryProperty(BaseModel):
    property_id: str
    property_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str
    zip_code: str | None = None
    county_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    total_units: int | None = None
    low_income_units: int | None = None
    placed_in_service_year: int | None = None
    construction_type: str | None = None
    distance_miles: float | None = None
    availability: Availability = Field(default_factory=Availability)
    fmr_reference: FmrReference | None = None
    mtsp_reference: MtspReference | None = None


class DiscoveryResponse(BaseModel):
    result_count: int
    filters_applied: list[AppliedFilter]
    ordering: Ordering
    properties: list[DiscoveryProperty]
    disclaimer: str = (
        "Availability and application acceptance are unknown. Results are not "
        "eligibility, approval, ranking, or recommendation decisions."
    )


def public_property_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Select only fields allowed to leave the public discovery boundary."""
    allowed = set(DiscoveryProperty.model_fields) - {
        "availability",
        "fmr_reference",
        "mtsp_reference",
        "distance_miles",
    }
    return {key: item.get(key) for key in allowed}
