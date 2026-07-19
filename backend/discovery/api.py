"""FastAPI route for HUD-backed property discovery."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError

from backend.discovery.repository import PropertyRepository
from backend.discovery.safety import forbidden_query_fields
from backend.discovery.schemas import (
    DiscoveryQuery,
    DiscoveryResponse,
    DiscoverySort,
)
from backend.discovery.service import DiscoveryService

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


def get_property_repository() -> PropertyRepository:
    return PropertyRepository()


def build_discovery_query(
    state: Annotated[str, Query(min_length=2, max_length=2)],
    city: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_miles: Annotated[float | None, Query(gt=0, le=100)] = None,
    bedrooms: Annotated[int | None, Query(ge=0, le=4)] = None,
    household_size: Annotated[int | None, Query(ge=1, le=8)] = None,
    sort_by: DiscoverySort = DiscoverySort.ALPHABETICAL,
) -> DiscoveryQuery:
    try:
        return DiscoveryQuery(
            state=state,
            city=city,
            latitude=latitude,
            longitude=longitude,
            radius_miles=radius_miles,
            bedrooms=bedrooms,
            household_size=household_size,
            sort_by=sort_by,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(
                include_context=False,
                include_input=False,
                include_url=False,
            ),
        ) from exc


@router.get("/properties", response_model=DiscoveryResponse)
def discover_properties(
    request: Request,
    query: Annotated[DiscoveryQuery, Depends(build_discovery_query)],
    repository: Annotated[PropertyRepository, Depends(get_property_repository)],
) -> DiscoveryResponse:
    forbidden = forbidden_query_fields(request.query_params.keys())
    if forbidden:
        raise HTTPException(
            status_code=400,
            detail=f"Discovery does not accept private or decisional filters: {', '.join(forbidden)}",
        )
    return DiscoveryService(repository).search(query)
