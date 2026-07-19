"""Firestore persistence boundary for public discovery data."""

from __future__ import annotations

from typing import Any

from backend.discovery.firebase_client import get_firestore_client


class PropertyRepository:
    def __init__(self, db=None) -> None:
        self.db = db or get_firestore_client()

    def find_by_location(
        self,
        *,
        state: str,
        city: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.db.collection("discovery_properties").where(
            "state", "==", state.upper()
        )
        if city:
            query = query.where(
                "city_normalized", "==", city.strip().casefold()
            )

        results: list[dict[str, Any]] = []
        for snapshot in query.stream():
            item = snapshot.to_dict() or {}
            item.setdefault("property_id", snapshot.id)
            results.append(item)
        return results

    def get_fmr_reference(
        self, area_id: str | None, *, fiscal_year: int = 2026
    ) -> dict[str, Any] | None:
        return self._get_reference("fmr_references", area_id, fiscal_year)

    def get_mtsp_reference(
        self, area_id: str | None, *, fiscal_year: int = 2026
    ) -> dict[str, Any] | None:
        return self._get_reference("mtsp_references", area_id, fiscal_year)

    def _get_reference(
        self, collection: str, area_id: str | None, fiscal_year: int
    ) -> dict[str, Any] | None:
        if not area_id:
            return None
        snapshot = (
            self.db.collection(collection)
            .document(f"{fiscal_year}_{area_id}")
            .get()
        )
        if not snapshot.exists:
            return None
        return snapshot.to_dict() or None
