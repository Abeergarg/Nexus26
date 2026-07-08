"""
Tests for core/constants.py — verifies all constants exist and have expected types.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.core.constants as C


class TestThresholdConstants:
    def test_heat_extreme_threshold_is_float(self):
        assert isinstance(C.HEAT_EXTREME_THRESHOLD, float)
        assert C.HEAT_EXTREME_THRESHOLD > 0

    def test_heat_high_threshold_less_than_extreme(self):
        assert C.HEAT_HIGH_THRESHOLD < C.HEAT_EXTREME_THRESHOLD

    def test_heat_caution_threshold_less_than_high(self):
        assert C.HEAT_CAUTION_THRESHOLD < C.HEAT_HIGH_THRESHOLD

    def test_water_critical_hours_is_positive(self):
        assert C.WATER_CRITICAL_HOURS > 0

    def test_ice_warning_hours_is_positive(self):
        assert C.ICE_WARNING_HOURS > 0

    def test_medical_warning_hours_is_positive(self):
        assert C.MEDICAL_WARNING_HOURS > 0


class TestRateConstants:
    def test_water_rate_factor_is_float(self):
        assert isinstance(C.WATER_RATE_FACTOR, float)
        assert C.WATER_RATE_FACTOR > 0

    def test_ice_rate_factor_is_float(self):
        assert isinstance(C.ICE_RATE_FACTOR, float)
        assert C.ICE_RATE_FACTOR > 0

    def test_medical_rate_divisor_is_positive(self):
        assert C.MEDICAL_RATE_DIVISOR > 0


class TestReplenishConstants:
    def test_replenish_values_are_non_negative(self):
        assert C.REPLENISH_WATER_PCT >= 0
        assert C.REPLENISH_MEDICAL_PCT >= 0
        assert C.REPLENISH_ICE_PCT >= 0

    def test_replenish_values_below_100(self):
        assert C.REPLENISH_WATER_PCT < 100
        assert C.REPLENISH_MEDICAL_PCT < 100
        assert C.REPLENISH_ICE_PCT < 100


class TestFallbackConstants:
    def test_fallback_temp_range_is_valid(self):
        assert C.FALLBACK_TEMP_MIN < C.FALLBACK_TEMP_MAX

    def test_fallback_humidity_range_is_valid(self):
        assert C.FALLBACK_HUMIDITY_MIN < C.FALLBACK_HUMIDITY_MAX

    def test_fallback_humidity_within_bounds(self):
        assert 0 <= C.FALLBACK_HUMIDITY_MIN <= 100
        assert 0 <= C.FALLBACK_HUMIDITY_MAX <= 100


class TestCacheConstants:
    def test_semantic_threshold_between_0_and_1(self):
        assert 0.0 < C.SEMANTIC_CACHE_THRESHOLD < 1.0


class TestRateLimitConstants:
    def test_rate_limit_requests_is_positive_int(self):
        assert isinstance(C.RATE_LIMIT_REQUESTS_PER_MINUTE, int)
        assert C.RATE_LIMIT_REQUESTS_PER_MINUTE > 0

    def test_rate_limit_window_is_positive_int(self):
        assert isinstance(C.RATE_LIMIT_WINDOW_SECONDS, int)
        assert C.RATE_LIMIT_WINDOW_SECONDS > 0


class TestTickConstants:
    def test_water_tick_range(self):
        assert C.WATER_TICK_MIN < C.WATER_TICK_MAX

    def test_ice_tick_range(self):
        assert C.ICE_TICK_MIN < C.ICE_TICK_MAX

    def test_medical_tick_range(self):
        assert C.MEDICAL_TICK_MIN < C.MEDICAL_TICK_MAX
