"""Deterministic fake clock for activity-event tests."""

__all__ = ["FakeClock"]


class FakeClock:
    """A :class:`Clock` returning a fixed ISO timestamp.

    If ``tick`` is provided it is appended as a suffix counter so repeated calls
    can be distinguished; by default the same fixed value is returned.
    """

    def __init__(self, fixed: str = "2026-07-19T00:00:00+00:00", tick: bool = False):
        self._fixed = fixed
        self._tick = tick
        self._count = 0

    def now_iso(self) -> str:
        if not self._tick:
            return self._fixed
        value = f"{self._fixed}#{self._count}"
        self._count += 1
        return value
