"""
Feature engineering for rate forecasting.

Pulls signals from the Signal Store for a given lane and transforms them
into a feature matrix the model can consume. This is the layer that
turns "raw signal time series" into "model-ready features" — rolling
averages, lags, ratios.

As the architecture doc notes (section 3), this can graduate into a
proper feature store as volume grows; at MVP, well-indexed queries
against the `signals` table are sufficient.
"""
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.signal import Signal

# Signals used as model inputs for rate forecasting. Extending this list
# is the primary way new signals translate into better forecasts —
# add the signal_id here once an adapter is producing it, then retrain.
FORECAST_INPUT_SIGNALS = [
    "customs_velocity_index",
    "port_dwell_time",
    # "ais_route_deviation",
    # "carrier_booking_velocity",
]


def build_feature_frame(db: Session, lane_id: str, as_of: datetime, lookback_days: int = 90) -> pd.DataFrame:
    """
    Build a feature DataFrame for `lane_id` as of `as_of`, using up to
    `lookback_days` of signal history.

    Returns a DataFrame indexed by date with one column per signal_id
    (raw value), plus derived rolling-average columns
    (`{signal_id}_7d_avg`, `{signal_id}_30d_avg`).

    Entity matching note: at MVP, port-level signals (entity_type="port")
    are matched to a lane via the lane's origin port (first 4 chars of
    lane_id, e.g. "SHSE" from "SHSE-LAX"). This is a simplification —
    V1 should introduce a proper lane->port mapping table.
    """
    start = as_of - timedelta(days=lookback_days)
    origin_port = lane_id.split("-")[0]

    stmt = select(Signal).where(
        Signal.signal_id.in_(FORECAST_INPUT_SIGNALS),
        Signal.timestamp >= start,
        Signal.timestamp <= as_of,
        (
            ((Signal.entity_type == "lane") & (Signal.entity_id == lane_id))
            | ((Signal.entity_type == "port") & (Signal.entity_id == origin_port))
        ),
    )

    rows = db.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        [{"date": r.timestamp.date(), "signal_id": r.signal_id, "value": r.value} for r in rows]
    )

    # Pivot to one column per signal, one row per date
    pivot = df.pivot_table(index="date", columns="signal_id", values="value", aggfunc="mean")
    pivot = pivot.sort_index().asfreq("D").ffill()

    # Derived rolling features
    for signal_id in FORECAST_INPUT_SIGNALS:
        if signal_id in pivot.columns:
            pivot[f"{signal_id}_7d_avg"] = pivot[signal_id].rolling(7, min_periods=1).mean()
            pivot[f"{signal_id}_30d_avg"] = pivot[signal_id].rolling(30, min_periods=1).mean()

    return pivot


def latest_feature_row(db: Session, lane_id: str, as_of: datetime) -> pd.DataFrame | None:
    """
    Convenience wrapper: returns just the most recent row of features
    (i.e. the input the model uses to make a forecast *right now*).
    Returns None if there's not enough history yet.
    """
    frame = build_feature_frame(db, lane_id, as_of)
    if frame.empty:
        return None
    return frame.tail(1)
