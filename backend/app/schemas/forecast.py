"""Pydantic schemas for Forecast endpoints."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SignalAttribution(BaseModel):
    signal_id: str
    value: float | None = None
    baseline_30d: float | None = None
    contribution: float | None = None
    note: str | None = None


class ForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_type: str
    entity_type: str
    entity_id: str
    generated_at: datetime
    target_date: date
    horizon_days: int
    predicted_value: float
    unit: str
    lower_bound: float | None
    upper_bound: float | None
    confidence: float
    model_version: str
    signal_attribution: list[SignalAttribution]


class LaneForecastSummary(BaseModel):
    """Summary view used by the dashboard's lane table — one row per lane."""
    lane_id: str
    current_value: float | None = None
    current_unit: str | None = None
    forecast_30d: ForecastRead | None = None
