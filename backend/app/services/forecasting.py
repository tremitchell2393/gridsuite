"""
Forecasting service — orchestrates daily forecast generation and the
accuracy validation loop.

Two responsibilities:
  1. `run_daily_forecasts`: for every actively-watched lane, generate
     30/60/90-day forecasts and write them to the `forecasts` table.
  2. `validate_past_forecasts`: for forecasts whose target_date has
     passed, look up the realized value and fill in
     Forecast.realized_value — this feeds the customer-facing accuracy
     dashboard AND the training data for future model improvements.
"""
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modeling.rate_forecast import predict_for_lane
from app.models.forecast import Forecast
from app.models.lane import WatchedLane
from app.models.signal import Signal

logger = logging.getLogger(__name__)

HORIZONS = [30, 60, 90]


def run_daily_forecasts() -> int:
    """
    Generate forecasts for every distinct lane currently watched by any
    organization. Returns the number of forecast rows written.

    Run once daily via the scheduler (app/services/scheduler.py), after
    the day's ingestion run completes.
    """
    db = SessionLocal()
    written = 0

    try:
        lane_ids = {row[0] for row in db.execute(select(WatchedLane.lane_id).distinct()).all()}

        for lane_id in lane_ids:
            for horizon in HORIZONS:
                forecast = predict_for_lane(db, lane_id, horizon_days=horizon)
                if forecast:
                    db.add(forecast)
                    written += 1

        db.commit()
    finally:
        db.close()

    logger.info("Daily forecast run complete: wrote %d forecasts for %d lanes", written, len(lane_ids))
    return written


def validate_past_forecasts() -> int:
    """
    Backfill `realized_value` for forecasts whose target_date has passed.

    Realized value is looked up from the `signals` table (signal_id=
    "spot_rate_change_pct" — i.e. the actual rate change observed over
    the same period the forecast was for). Returns count of forecasts
    updated.
    """
    db = SessionLocal()
    updated = 0
    today = datetime.now(UTC).date()

    try:
        stmt = select(Forecast).where(
            Forecast.target_date <= today,
            Forecast.realized_value.is_(None),
        )
        pending = db.execute(stmt).scalars().all()

        for forecast in pending:
            realized = _lookup_realized_value(db, forecast)
            if realized is not None:
                forecast.realized_value = realized
                updated += 1

        db.commit()
    finally:
        db.close()

    logger.info("Forecast validation: updated %d of %d pending forecasts", updated, len(pending))
    return updated


def _lookup_realized_value(db: Session, forecast: Forecast) -> float | None:
    """
    Find the actual rate change for the lane/period this forecast was
    for. Returns None if the realized signal isn't available yet
    (e.g. data lag) — the forecast stays pending and is retried on the
    next validation run.
    """
    stmt = (
        select(Signal)
        .where(
            Signal.entity_type == forecast.entity_type,
            Signal.entity_id == forecast.entity_id,
            Signal.signal_id == "spot_rate_change_pct",
            Signal.timestamp >= datetime.combine(forecast.target_date, datetime.min.time(), tzinfo=UTC),
        )
        .order_by(Signal.timestamp.asc())
        .limit(1)
    )
    result = db.execute(stmt).scalar_one_or_none()
    return result.value if result else None
