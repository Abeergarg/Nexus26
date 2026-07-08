"""
Operational forecasting service for Project Nexus26.

Provides heat index calculation (NOAA Rothfusz regression) and live resource
depletion forecasting based on attendance, weather conditions, and current
inventory levels.
"""

import random
from typing import Any, Dict

from app.core.constants import (
    HEAT_CAUTION_THRESHOLD,
    HEAT_EXTREME_THRESHOLD,
    HEAT_HIGH_THRESHOLD,
    HEAT_MULTIPLIER_BASE_TEMP,
    HEAT_MULTIPLIER_RATE,
    ICE_DISPATCH_BAGS,
    ICE_TICK_MAX,
    ICE_TICK_MIN,
    ICE_WARNING_HOURS,
    MEDICAL_DISPATCH_KITS,
    MEDICAL_HEAT_BASE_TEMP,
    MEDICAL_HEAT_RATE,
    MEDICAL_RATE_DIVISOR,
    MEDICAL_TICK_MAX,
    MEDICAL_TICK_MIN,
    MEDICAL_WARNING_HOURS,
    REPLENISH_ICE_PCT,
    REPLENISH_MEDICAL_PCT,
    REPLENISH_WATER_PCT,
    WATER_CRITICAL_HOURS,
    WATER_DISPATCH_LITERS,
    WATER_RATE_FACTOR,
    ICE_RATE_FACTOR,
    WATER_TICK_MAX,
    WATER_TICK_MIN,
)
from app.core.logging import get_structured_logger, log_execution_time

logger = get_structured_logger("ForecastingService")

# Fahrenheit conversion constants
_CELSIUS_TO_FAHRENHEIT_SCALE: float = 9.0 / 5.0
_FAHRENHEIT_OFFSET: float = 32.0


def calculate_heat_index(temp_c: float, rh: float) -> float:
    """
    Calculates the Heat Index (HI) in Celsius using the NOAA Rothfusz regression.

    For mild conditions a simplified formula is used. For high temperatures
    (HI ≥ 80°F) the full Rothfusz regression is applied with two adjustment
    corrections for low-humidity and high-humidity edge cases.

    Args:
        temp_c: Ambient air temperature in degrees Celsius.
        rh: Relative humidity as a percentage (0–100).

    Returns:
        Calculated heat index in degrees Celsius.
    """
    t_f = temp_c * _CELSIUS_TO_FAHRENHEIT_SCALE + _FAHRENHEIT_OFFSET

    # Simple estimate (valid when HI < 80°F)
    hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))

    # Full Rothfusz regression for high temperatures
    if hi_f >= 80.0:
        hi_f = (
            -42.379
            + 2.04901523 * t_f
            + 10.14333127 * rh
            - 0.22475541 * t_f * rh
            - 0.00683783 * t_f * t_f
            - 0.05481717 * rh * rh
            + 0.00122874 * t_f * t_f * rh
            + 0.00085282 * t_f * rh * rh
            - 0.00000199 * t_f * t_f * rh * rh
        )

        # Low-humidity adjustment (dry heat)
        if rh < 13.0 and 80.0 <= t_f <= 112.0:
            import math

            adj = ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
            hi_f -= adj
        # High-humidity adjustment (muggy heat)
        elif rh > 85.0 and 80.0 <= t_f <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
            hi_f += adj

    return (hi_f - _FAHRENHEIT_OFFSET) * 5.0 / 9.0


class ForecastingService:
    """
    Live resource depletion forecasting service.

    Tracks inventory levels for water, ice, and medical kits.
    Calculates consumption rates and time-to-depletion based on attendance
    and heat index conditions. Issues alerts and dispatch actions when
    thresholds are breached.
    """

    # Base inventory levels
    INITIAL_WATER_LITERS: float = 50_000.0
    INITIAL_MEDICAL_KITS: int = 1_000
    INITIAL_ICE_BAGS: int = 5_000

    def __init__(self) -> None:
        self.water_liters: float = self.INITIAL_WATER_LITERS
        self.medical_kits: int = self.INITIAL_MEDICAL_KITS
        self.ice_bags: int = self.INITIAL_ICE_BAGS

        self.water_depleted_pct: float = 12.5
        self.medical_depleted_pct: float = 4.0
        self.ice_depleted_pct: float = 8.0

    @log_execution_time("ForecastingService")
    def generate_live_operations_forecast(
        self, attendance: int, current_temp_c: float, current_humidity: float
    ) -> Dict[str, Any]:
        """
        Generates a comprehensive real-time operations forecast.

        Calculates heat index, consumption rates, time-to-depletion estimates,
        automated alerts, and dispatch recommendations.

        Args:
            attendance: Current venue occupancy (number of people).
            current_temp_c: Current ambient temperature in Celsius.
            current_humidity: Current relative humidity as a percentage.

        Returns:
            Dictionary containing heat metrics, consumption rates, remaining time
            estimates, depletion percentages, alerts, and dispatch actions.
        """
        heat_index_c = calculate_heat_index(current_temp_c, current_humidity)

        heat_multiplier = 1.0
        if heat_index_c > HEAT_MULTIPLIER_BASE_TEMP:
            heat_multiplier += (
                heat_index_c - HEAT_MULTIPLIER_BASE_TEMP
            ) * HEAT_MULTIPLIER_RATE

        water_rate_per_hr = attendance * WATER_RATE_FACTOR * heat_multiplier
        ice_rate_per_hr = attendance * ICE_RATE_FACTOR * heat_multiplier
        medical_incident_rate_per_hr = (attendance / MEDICAL_RATE_DIVISOR) * (
            1.0 + max(0.0, heat_index_c - MEDICAL_HEAT_BASE_TEMP) * MEDICAL_HEAT_RATE
        )

        remaining_water = self.water_liters * (1.0 - self.water_depleted_pct / 100.0)
        remaining_ice = self.ice_bags * (1.0 - self.ice_depleted_pct / 100.0)
        remaining_med = self.medical_kits * (1.0 - self.medical_depleted_pct / 100.0)

        water_hours_left = remaining_water / max(1.0, water_rate_per_hr)
        ice_hours_left = remaining_ice / max(1.0, ice_rate_per_hr)
        med_hours_left = remaining_med / max(0.1, medical_incident_rate_per_hr)

        alerts = []
        dispatch_actions = []

        if water_hours_left < WATER_CRITICAL_HOURS:
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "resource": "Water Reserves",
                    "message": (
                        f"Water depletion imminent in {round(water_hours_left, 1)} hrs "
                        f"due to heat index ({round(heat_index_c, 1)}C)."
                    ),
                }
            )
            dispatch_actions.append(
                {
                    "action": "DISPATCH_WATER_TRUCK",
                    "target_zone": "Food_Court_1",
                    "quantity": WATER_DISPATCH_LITERS,
                    "unit": "Liters",
                    "volunteer_group": "Section 100 Logistics Support",
                }
            )
            logger.warning(
                "CRITICAL: Water supply below critical threshold.",
                extra={
                    "hours_remaining": water_hours_left,
                    "heat_index_c": heat_index_c,
                },
            )

        if med_hours_left < MEDICAL_WARNING_HOURS:
            alerts.append(
                {
                    "severity": "WARNING",
                    "resource": "Medical Responders",
                    "message": f"Medical supply exhaustion projected in {round(med_hours_left, 1)} hrs.",
                }
            )
            dispatch_actions.append(
                {
                    "action": "RESTOCK_FIRST_AID",
                    "target_zone": "First_Aid_1",
                    "quantity": MEDICAL_DISPATCH_KITS,
                    "unit": "Kits",
                    "volunteer_group": "Red Cross Field Unit A",
                }
            )

        if ice_hours_left < ICE_WARNING_HOURS:
            alerts.append(
                {
                    "severity": "WARNING",
                    "resource": "Ice Inventories",
                    "message": f"Ice supply depletion warning: {round(ice_hours_left, 1)} hrs remaining.",
                }
            )
            dispatch_actions.append(
                {
                    "action": "DISPATCH_ICE_CARTS",
                    "target_zone": "Food_Court_1",
                    "quantity": ICE_DISPATCH_BAGS,
                    "unit": "Bags",
                    "volunteer_group": "Concession Runners",
                }
            )

        danger_level = "LOW"
        if heat_index_c >= HEAT_EXTREME_THRESHOLD:
            danger_level = "EXTREME DANGER"
        elif heat_index_c >= HEAT_HIGH_THRESHOLD:
            danger_level = "HIGH RISK (HEAT CRAMPS/EXHAUSTION)"
        elif heat_index_c >= HEAT_CAUTION_THRESHOLD:
            danger_level = "CAUTION"

        return {
            "heat_index_celsius": round(heat_index_c, 1),
            "heat_index_fahrenheit": round(
                heat_index_c * _CELSIUS_TO_FAHRENHEIT_SCALE + _FAHRENHEIT_OFFSET, 1
            ),
            "danger_level": danger_level,
            "consumption_rates": {
                "water_liters_per_hr": round(water_rate_per_hr, 1),
                "ice_bags_per_hr": round(ice_rate_per_hr, 1),
                "medical_incidents_per_hr": round(medical_incident_rate_per_hr, 2),
            },
            "remaining_time_hours": {
                "water": round(water_hours_left, 1),
                "ice": round(ice_hours_left, 1),
                "medical": round(med_hours_left, 1),
            },
            "depletion_percentages": {
                "water": round(self.water_depleted_pct, 1),
                "ice": round(self.ice_depleted_pct, 1),
                "medical": round(self.medical_depleted_pct, 1),
            },
            "alerts": alerts,
            "dispatch_actions": dispatch_actions,
        }

    def simulate_tick(self) -> None:
        """
        Advances inventory depletion by one simulation tick.

        Increments each resource's depletion percentage by a random amount
        within its configured tick range, capped at 100%.
        """
        self.water_depleted_pct = min(
            100.0,
            self.water_depleted_pct + random.uniform(WATER_TICK_MIN, WATER_TICK_MAX),
        )
        self.medical_depleted_pct = min(
            100.0,
            self.medical_depleted_pct
            + random.uniform(MEDICAL_TICK_MIN, MEDICAL_TICK_MAX),
        )
        self.ice_depleted_pct = min(
            100.0, self.ice_depleted_pct + random.uniform(ICE_TICK_MIN, ICE_TICK_MAX)
        )

    def trigger_replenish(self) -> None:
        """
        Resets all resource depletion percentages to near-full levels.

        Called when an Administrator triggers the supply replenishment action.
        """
        self.water_depleted_pct = REPLENISH_WATER_PCT
        self.medical_depleted_pct = REPLENISH_MEDICAL_PCT
        self.ice_depleted_pct = REPLENISH_ICE_PCT
        logger.info("All resources replenished to peak capacity.")


# Global service singleton
forecasting_service = ForecastingService()
