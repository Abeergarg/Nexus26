"""
Centralized named constants for Project Nexus26.

All magic numbers, threshold values, and domain constants are defined here.
Import from this module instead of scattering literals throughout the codebase.
"""

# ---------------------------------------------------------------------------
# Heat Index Danger Thresholds (°C)
# ---------------------------------------------------------------------------
HEAT_EXTREME_THRESHOLD: float = 41.0
"""Heat index above this value triggers EXTREME DANGER classification."""

HEAT_HIGH_THRESHOLD: float = 35.0
"""Heat index above this value triggers HIGH RISK (HEAT CRAMPS/EXHAUSTION)."""

HEAT_CAUTION_THRESHOLD: float = 27.0
"""Heat index above this value triggers CAUTION classification."""

HEAT_MULTIPLIER_BASE_TEMP: float = 22.0
"""Base temperature (°C) above which the heat consumption multiplier activates."""

HEAT_MULTIPLIER_RATE: float = 0.15
"""Rate at which consumption multiplier grows per degree above base temp."""

# ---------------------------------------------------------------------------
# Resource Alert Thresholds (hours remaining)
# ---------------------------------------------------------------------------
WATER_CRITICAL_HOURS: float = 3.0
"""Remaining water supply hours that trigger a CRITICAL alert."""

ICE_WARNING_HOURS: float = 4.0
"""Remaining ice supply hours that trigger a WARNING alert."""

MEDICAL_WARNING_HOURS: float = 6.0
"""Remaining medical kit hours that trigger a WARNING alert."""

# ---------------------------------------------------------------------------
# Consumption Rate Factors (per-attendee per-hour)
# ---------------------------------------------------------------------------
WATER_RATE_FACTOR: float = 0.25
"""Liters of water consumed per attendee per hour at baseline."""

ICE_RATE_FACTOR: float = 0.02
"""Ice bags consumed per attendee per hour at baseline."""

MEDICAL_RATE_DIVISOR: float = 2000.0
"""Attendee divisor for medical incident rate calculation."""

MEDICAL_HEAT_RATE: float = 0.3
"""Additional medical incident rate per degree above 25°C heat index."""

MEDICAL_HEAT_BASE_TEMP: float = 25.0
"""Heat index base temperature (°C) for medical rate calculation."""

# ---------------------------------------------------------------------------
# Speed & Physics
# ---------------------------------------------------------------------------
WALKING_SPEED_MPS: float = 1.4
"""Baseline pedestrian walking speed in meters per second."""

DENSITY_SPEED_FACTOR: float = 0.7
"""Factor by which crowd density reduces walking speed (0.0–1.0)."""

DENSITY_COST_STANDARD: float = 9.0
"""Dijkstra cost multiplier for crowd density on standard routes."""

DENSITY_COST_MOBILITY: float = 4.0
"""Dijkstra cost multiplier for crowd density on accessibility routes."""

CARBON_FACTOR: float = 100.0
"""Carbon emission factor: grams CO2 per (distance × (1 - green_factor))."""

# ---------------------------------------------------------------------------
# Replenish Reset Values (% depleted)
# ---------------------------------------------------------------------------
REPLENISH_WATER_PCT: float = 5.0
"""Water depletion percentage after replenishment."""

REPLENISH_MEDICAL_PCT: float = 2.0
"""Medical depletion percentage after replenishment."""

REPLENISH_ICE_PCT: float = 3.0
"""Ice depletion percentage after replenishment."""

# ---------------------------------------------------------------------------
# Simulation Tick Ranges (% depletion increase per tick)
# ---------------------------------------------------------------------------
WATER_TICK_MIN: float = 0.1
WATER_TICK_MAX: float = 0.4
ICE_TICK_MIN: float = 0.05
ICE_TICK_MAX: float = 0.25
MEDICAL_TICK_MIN: float = 0.02
MEDICAL_TICK_MAX: float = 0.1

# ---------------------------------------------------------------------------
# Fallback Weather (when all API retries fail)
# ---------------------------------------------------------------------------
FALLBACK_TEMP_MIN: float = 29.0
FALLBACK_TEMP_MAX: float = 34.0
FALLBACK_HUMIDITY_MIN: float = 50.0
FALLBACK_HUMIDITY_MAX: float = 70.0

# ---------------------------------------------------------------------------
# Dispatch Quantities
# ---------------------------------------------------------------------------
WATER_DISPATCH_LITERS: int = 10000
ICE_DISPATCH_BAGS: int = 500
MEDICAL_DISPATCH_KITS: int = 100

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
SEMANTIC_CACHE_THRESHOLD: float = 0.82
"""Minimum cosine similarity score for a semantic cache hit on route queries."""

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
"""Maximum number of requests allowed per IP per minute."""

RATE_LIMIT_WINDOW_SECONDS: int = 60
"""Sliding window duration in seconds for rate limiting."""

# ---------------------------------------------------------------------------
# Crowd Density
# ---------------------------------------------------------------------------
DENSITY_MIN: float = 0.0
DENSITY_MAX: float = 1.0

# ---------------------------------------------------------------------------
# Backoff
# ---------------------------------------------------------------------------
BACKOFF_BASE_SECONDS: float = 0.25
"""Base value for exponential backoff: sleep = base * 2^attempt."""
