"""
Forecast routes — serve pre-computed forecasts to the dashboard and
external API.

Per architecture doc section 4: forecasts are read-only here. They're
written by the daily inference job (app/services/forecasting.py), not
generated on-demand by these endpoints — keeps API latency independent
of model complexity.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_organization, get_current_user
from app.db.session import get_db
from app.models.forecast import Forecast
from app.models.organization import Organization
from app.models.signal import Signal
from app.schemas.forecast import ForecastRead, LaneForecastSummary

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/lane/{lane_id}", response_model=list[ForecastRead])
def get_lane_forecasts(
    lane_id: str,
    horizon_days: int | None = Query(None, description="Filter to a specific horizon (30/60/90)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Returns the most recent forecast(s) for a lane. If `horizon_days` is
    omitted, returns the latest forecast for each available horizon
    (used by the Lane Detail page to show 30/60/90-day forecasts
    together).
    """
    stmt = select(Forecast).where(
        Forecast.entity_type == "lane",
        Forecast.entity_id == lane_id,
        Forecast.forecast_type == "rate_change_pct",
    )
    if horizon_days:
        stmt = stmt.where(Forecast.horizon_days == horizon_days)

    stmt = stmt.order_by(Forecast.generated_at.desc())
    rows = db.execute(stmt).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No forecasts found for lane {lane_id}")

    if horizon_days:
        return [rows[0]]

    # Latest forecast per horizon
    latest_by_horizon: dict[int, Forecast] = {}
    for row in rows:
        if row.horizon_days not in latest_by_horizon:
            latest_by_horizon[row.horizon_days] = row

    return list(latest_by_horizon.values())


@router.get("/dashboard", response_model=list[LaneForecastSummary])
def get_dashboard_summary(
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    """
    Returns a summary row per watched lane for this organization's
    dashboard: current value + 30-day forecast. Powers the lane table
    on the Overview screen.
    """
    summaries = []

    for watched in org.watched_lanes if hasattr(org, "watched_lanes") else []:
        lane_id = watched.lane_id
        summaries.append(_build_lane_summary(db, lane_id))

    return summaries


def _build_lane_summary(db: Session, lane_id: str) -> LaneForecastSummary:
    # Most recent rate signal for "current value" (if a rate signal
    # exists for this lane — depends on whether a rate-index adapter has
    # been added yet).
    current_stmt = (
        select(Signal)
        .where(Signal.entity_type == "lane", Signal.entity_id == lane_id, Signal.signal_id == "spot_rate")
        .order_by(Signal.timestamp.desc())
        .limit(1)
    )
    current = db.execute(current_stmt).scalar_one_or_none()

    forecast_stmt = (
        select(Forecast)
        .where(
            Forecast.entity_type == "lane",
            Forecast.entity_id == lane_id,
            Forecast.forecast_type == "rate_change_pct",
            Forecast.horizon_days == 30,
        )
        .order_by(Forecast.generated_at.desc())
        .limit(1)
    )
    forecast = db.execute(forecast_stmt).scalar_one_or_none()

    return LaneForecastSummary(
        lane_id=lane_id,
        current_value=current.value if current else None,
        current_unit=current.unit if current else None,
        forecast_30d=ForecastRead.model_validate(forecast) if forecast else None,
    )
