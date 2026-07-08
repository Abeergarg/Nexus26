import sys
import os

# Ensure backend folder is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.features.operations.service import calculate_heat_index, forecasting_service


def test_heat_index_NOAA_formula():
    # Mild temperature and moderate humidity (22C, 50% RH)
    hi_mild = calculate_heat_index(22.0, 50.0)
    assert hi_mild < 25.0

    # Severe temperature (35C, 75% RH)
    hi_severe = calculate_heat_index(35.0, 75.0)
    assert hi_severe > 42.0  # Extreme Danger index


def test_resource_depletion_forecasts():
    forecast = forecasting_service.generate_live_operations_forecast(
        attendance=65000, current_temp_c=36.0, current_humidity=70.0
    )

    assert forecast["heat_index_celsius"] > 40.0
    assert len(forecast["alerts"]) >= 1
    assert any(alert["severity"] == "CRITICAL" for alert in forecast["alerts"])
