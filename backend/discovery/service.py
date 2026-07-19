"""Application service for public, non-decisional property discovery."""

from __future__ import annotations

from typing import Any

from backend.discovery.distance import distance_miles, valid_coordinates
from backend.discovery.safety import assert_public_property
from backend.discovery.schemas import (
    AppliedFilter,
    DiscoveryProperty,
    DiscoveryQuery,
    DiscoveryResponse,
    DiscoverySort,
    FmrReference,
    MtspReference,
    Ordering,
    public_property_fields,
)

FMR_FIELDS = {
    0: "efficiency",
    1: "bedroom_1",
    2: "bedroom_2",
    3: "bedroom_3",
    4: "bedroom_4",
}


class DiscoveryService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def search(self, query: DiscoveryQuery) -> DiscoveryResponse:
        source_properties = self.repository.find_by_location(
            state=query.state,
            city=query.city,
        )
        fmr_cache: dict[str, dict[str, Any] | None] = {}
        mtsp_cache: dict[str, dict[str, Any] | None] = {}
        properties: list[DiscoveryProperty] = []

        for item in source_properties:
            assert_public_property(item)
            distance = self._property_distance(item, query)
            if query.radius_miles is not None and (
                distance is None or distance > query.radius_miles
            ):
                continue

            fmr = self._fmr_reference(item, query.bedrooms, fmr_cache)
            mtsp = self._mtsp_reference(
                item, query.household_size, mtsp_cache
            )
            properties.append(
                DiscoveryProperty(
                    **public_property_fields(item),
                    distance_miles=round(distance, 1) if distance is not None else None,
                    fmr_reference=fmr,
                    mtsp_reference=mtsp,
                )
            )

        self._sort(properties, query.sort_by)
        return DiscoveryResponse(
            result_count=len(properties),
            filters_applied=self._filters(query),
            ordering=Ordering(method=query.sort_by),
            properties=properties,
        )

    @staticmethod
    def _property_distance(
        item: dict[str, Any], query: DiscoveryQuery
    ) -> float | None:
        if query.latitude is None or query.longitude is None:
            return None
        if not valid_coordinates(item.get("latitude"), item.get("longitude")):
            return None
        return distance_miles(
            query.latitude,
            query.longitude,
            float(item["latitude"]),
            float(item["longitude"]),
        )

    def _fmr_reference(
        self,
        item: dict[str, Any],
        bedrooms: int | None,
        cache: dict[str, dict[str, Any] | None],
    ) -> FmrReference | None:
        area_id = item.get("fmr_area_id")
        if bedrooms is None or not area_id:
            return None
        if area_id not in cache:
            cache[area_id] = self.repository.get_fmr_reference(area_id)
        reference = cache[area_id]
        if reference is None:
            return None
        return FmrReference(
            fiscal_year=int(reference.get("fiscal_year", 2026)),
            bedrooms=bedrooms,
            amount=reference.get(FMR_FIELDS[bedrooms]),
        )

    def _mtsp_reference(
        self,
        item: dict[str, Any],
        household_size: int | None,
        cache: dict[str, dict[str, Any] | None],
    ) -> MtspReference | None:
        area_id = item.get("mtsp_area_id")
        if household_size is None or not area_id:
            return None
        if area_id not in cache:
            cache[area_id] = self.repository.get_mtsp_reference(area_id)
        reference = cache[area_id]
        if reference is None:
            return None
        limits = reference.get("limits_60_percent") or {}
        return MtspReference(
            fiscal_year=int(reference.get("fiscal_year", 2026)),
            household_size=household_size,
            income_limit=limits.get(str(household_size)),
        )

    @staticmethod
    def _sort(
        properties: list[DiscoveryProperty], method: DiscoverySort
    ) -> None:
        if method == DiscoverySort.DISTANCE:
            properties.sort(
                key=lambda item: (
                    item.distance_miles is None,
                    item.distance_miles or 0,
                    (item.property_name or "").casefold(),
                    item.property_id,
                )
            )
            return
        properties.sort(
            key=lambda item: (
                (item.property_name or "").casefold(),
                item.property_id,
            )
        )

    @staticmethod
    def _filters(query: DiscoveryQuery) -> list[AppliedFilter]:
        values = [
            ("state", query.state),
            ("city", query.city),
            ("latitude", query.latitude),
            ("longitude", query.longitude),
            ("radius_miles", query.radius_miles),
            ("bedrooms", query.bedrooms),
            ("household_size", query.household_size),
        ]
        return [
            AppliedFilter(field=field, value=value)
            for field, value in values
            if value is not None
        ]
