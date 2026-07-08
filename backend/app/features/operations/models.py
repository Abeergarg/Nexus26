from pydantic import BaseModel, Field
from typing import List, Dict, Any


class WeatherInput(BaseModel):
    temperature_celsius: float
    humidity_percentage: float


class DispatchAction(BaseModel):
    action: str
    target_zone: str
    quantity: int
    unit: str
    volunteer_group: str


class OperationsAlert(BaseModel):
    severity: str
    resource: str
    message: str


class ForecastResponse(BaseModel):
    heat_index_celsius: float
    heat_index_fahrenheit: float
    danger_level: str
    consumption_rates: Dict[str, float]
    remaining_time_hours: Dict[str, float]
    depletion_percentages: Dict[str, float]
    alerts: List[OperationsAlert]
    dispatch_actions: List[DispatchAction]
    inputs: Dict[str, Any] = Field(
        ..., description="Details of the weather conditions and attendance used"
    )
