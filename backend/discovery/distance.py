"""Geographic helpers for ephemeral discovery searches."""

from __future__ import annotations

import math

EARTH_RADIUS_MILES = 3958.7613


def valid_coordinates(latitude: object, longitude: object) -> bool:
    """Return whether two values form a finite WGS84 coordinate pair."""
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    )


def distance_miles(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Calculate great-circle distance using the haversine formula."""
    if not valid_coordinates(latitude_a, longitude_a) or not valid_coordinates(
        latitude_b, longitude_b
    ):
        raise ValueError("latitude/longitude must be finite WGS84 coordinates")

    lat_a, lon_a, lat_b, lon_b = map(
        math.radians,
        (latitude_a, longitude_a, latitude_b, longitude_b),
    )
    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    central_angle = 2 * math.atan2(
        math.sqrt(haversine), math.sqrt(1 - haversine)
    )
    return EARTH_RADIUS_MILES * central_angle
