from enum import StrEnum


class RequestRoute(StrEnum):
    CHAT = "CHAT"
    READINESS = "READINESS"
    SAFETY = "SAFETY"
    PROVENANCE = "PROVENANCE"


def select_route(request_type: str) -> RequestRoute:
    normalized = request_type.strip().upper()
    try:
        return RequestRoute(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported AI Developer 2 request type: {request_type}") from exc
