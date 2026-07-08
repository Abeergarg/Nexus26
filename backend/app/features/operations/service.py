import math
import random
from typing import Dict, Any


def calculate_heat_index(temp_c: float, rh: float) -> float:
    """
    Calculates Heat Index (HI) in Celsius using the standard NOAA Rothfusz regression.
    """
    t_f = temp_c * 9.0 / 5.0 + 32.0

    # 1. Simple formula for mild conditions
    hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))

    # 2. Rothfusz regression for high temperatures
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

        # Adjustments
        if rh < 13.0 and (80.0 <= t_f <= 112.0):
            adj = ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
            hi_f -= adj
        elif rh > 85.0 and (80.0 <= t_f <= 87.0):
            adj = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
            hi_f += adj

    return (hi_f - 32.0) * 5.0 / 9.0


class ForecastingService:
    def __init__(self):
        # Base inventories
        self.water_liters = 50000.0
        self.medical_kits = 1000
        self.ice_bags = 5000

        # Current depletion percentages
        self.water_depleted_pct = 12.5
        self.medical_depleted_pct = 4.0
        self.ice_depleted_pct = 8.0

    def generate_live_operations_forecast(
        self, attendance: int, current_temp_c: float, current_humidity: float
    ) -> Dict[str, Any]:
        heat_index_c = calculate_heat_index(current_temp_c, current_humidity)

        heat_multiplier = 1.0
        if heat_index_c > 22.0:
            heat_multiplier += (heat_index_c - 22.0) * 0.15

        water_rate_per_hr = attendance * 0.25 * heat_multiplier
        ice_rate_per_hr = attendance * 0.02 * heat_multiplier
        medical_incident_rate_per_hr = (attendance / 2000.0) * (
            1.0 + max(0.0, heat_index_c - 25.0) * 0.3
        )

        remaining_water = self.water_liters * (1.0 - self.water_depleted_pct / 100.0)
        remaining_ice = self.ice_bags * (1.0 - self.ice_depleted_pct / 100.0)
        remaining_med = self.medical_kits * (1.0 - self.medical_depleted_pct / 100.0)

        water_hours_left = remaining_water / max(1.0, water_rate_per_hr)
        ice_hours_left = remaining_ice / max(1.0, ice_rate_per_hr)
        med_hours_left = remaining_med / max(0.1, medical_incident_rate_per_hr)

        alerts = []
        dispatch_actions = []

        if water_hours_left < 3.0:
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
                    "quantity": 10000,
                    "unit": "Liters",
                    "volunteer_group": "Section 100 Logistics Support",
                }
            )

        if med_hours_left < 6.0:
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
                    "quantity": 100,
                    "unit": "Kits",
                    "volunteer_group": "Red Cross Field Unit A",
                }
            )

        if ice_hours_left < 4.0:
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
                    "quantity": 500,
                    "unit": "Bags",
                    "volunteer_group": "Concession Runners",
                }
            )

        danger_level = "LOW"
        if heat_index_c >= 41.0:
            danger_level = "EXTREME DANGER"
        elif heat_index_c >= 35.0:
            danger_level = "HIGH RISK (HEAT CRAMPS/EXHAUSTION)"
        elif heat_index_c >= 27.0:
            danger_level = "CAUTION"

        return {
            "heat_index_celsius": round(heat_index_c, 1),
            "heat_index_fahrenheit": round(heat_index_c * 9.0 / 5.0 + 32.0, 1),
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

    def simulate_tick(self):
        self.water_depleted_pct = min(
            100.0, self.water_depleted_pct + random.uniform(0.1, 0.4)
        )
        self.medical_depleted_pct = min(
            100.0, self.medical_depleted_pct + random.uniform(0.02, 0.1)
        )
        self.ice_depleted_pct = min(
            100.0, self.ice_depleted_pct + random.uniform(0.05, 0.25)
        )

    def trigger_replenish(self):
        self.water_depleted_pct = 5.0
        self.medical_depleted_pct = 2.0
        self.ice_depleted_pct = 3.0


# Global service instance
forecasting_service = ForecastingService()
