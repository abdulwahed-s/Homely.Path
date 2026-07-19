"""Configuration constants for the Profile Reconciliation Agent."""

# Absolute tolerance (in dollars) when comparing regular_hours x hourly_rate
# against the displayed gross_pay. Kept tight so the organizer HH-002 fixture
# (960 vs 1395) trips while exact stubs (e.g. 76 x 28.5 == 2166) do not.
GROSS_TOLERANCE = 0.01
