"""
Rate forecasting model.

MVP approach (per architecture doc section 4): gradient boosting
(XGBoost) with quantile regression for confidence bands, trained on
engineered signal features. Simple, explainable, fast to iterate.

This module covers both training (`train`) and inference
(`predict_for_lane`). Training runs on a schedule (weekly); inference
runs daily per lane and writes results to the `forecasts` table — the
API never calls `predict_for_lane` directly (see architecture doc
section 4: "inference is batch-scored, not on-demand").
"""
import logging
from datetime import UTC, datetime, timedelta

import joblib
import pandas as pd
import xgboost as xgb
from sqlalchemy.orm import Session

from app.modeling.features import FORECAST_INPUT_SIGNALS, build_feature_frame, latest_feature_row
from app.models.forecast import Forecast

logger = logging.getLogger(__name__)

MODEL_VERSION = "rate_forecast_v0.1"
MODEL_DIR = "./data/models"

# Quantiles for confidence bands: lower bound, point estimate, upper bound
QUANTILES = [0.1, 0.5, 0.9]


def _model_path(lane_id: str, horizon_days: int, quantile: float) -> str:
    return f"{MODEL_DIR}/{lane_id}_{horizon_days}d_q{int(quantile*100)}.joblib"


def train(db: Session, lane_id: str, horizon_days: int = 30) -> None:
    """
    Train (or retrain) the rate forecast model for a single lane and
    horizon. Trains one XGBoost model per quantile in QUANTILES, saved
    to MODEL_DIR.

    Training data: historical features joined with the realized rate
    change `horizon_days` later. At true MVP (before enough history
    exists), this function will simply log a warning and exit — the
    system falls back to a naive baseline (see `_naive_forecast` below)
    until enough training data accumulates.
    """
    import os
    os.makedirs(MODEL_DIR, exist_ok=True)

    frame = build_feature_frame(db, lane_id, as_of=datetime.now(UTC), lookback_days=365)

    if frame.empty or len(frame) < horizon_days + 30:
        logger.warning(
            "Not enough history to train model for lane=%s horizon=%d (have %d rows). "
            "Falling back to naive forecasting until more data accumulates.",
            lane_id, horizon_days, len(frame),
        )
        return

    # Target: rate_change_pct `horizon_days` ahead. NOTE: this assumes a
    # `rate_change_pct` signal/column exists in the feature frame once
    # a rate-index adapter is added. Placeholder logic shown for
    # structure — real implementation joins against realized rates.
    if "rate_change_pct" not in frame.columns:
        logger.warning("rate_change_pct not in feature frame for lane=%s — skipping training.", lane_id)
        return

    target = frame["rate_change_pct"].shift(-horizon_days)
    features = frame.drop(columns=["rate_change_pct"])

    valid = target.notna()
    X, y = features[valid], target[valid]

    for q in QUANTILES:
        model = xgb.XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=q,
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
        )
        model.fit(X, y)
        joblib.dump(model, _model_path(lane_id, horizon_days, q))

    logger.info("Trained models for lane=%s horizon=%d on %d rows", lane_id, horizon_days, len(X))


def predict_for_lane(db: Session, lane_id: str, horizon_days: int = 30) -> Forecast | None:
    """
    Generate a forecast for `lane_id` at `horizon_days` out, using the
    most recent feature data. Returns a Forecast ORM instance (not yet
    committed — caller decides whether/when to add+commit, typically the
    daily inference job in app/services/forecasting.py).

    Falls back to `_naive_forecast` if no trained model exists yet —
    this keeps the dashboard populated with *something* reasonable
    (a persistence forecast: "rate stays flat, low confidence") during
    the early period before enough history exists for real models.
    """
    features = latest_feature_row(db, lane_id, as_of=datetime.now(UTC))

    if features is None:
        logger.warning("No feature data available for lane=%s — skipping forecast.", lane_id)
        return None

    try:
        predictions = {}
        for q in QUANTILES:
            model = joblib.load(_model_path(lane_id, horizon_days, q))
            X = features.drop(columns=["rate_change_pct"], errors="ignore")
            predictions[q] = float(model.predict(X)[0])

        point_estimate = predictions[0.5]
        lower, upper = predictions[0.1], predictions[0.9]
        confidence = _confidence_from_spread(lower, upper)
        attribution = _compute_attribution(features)

    except FileNotFoundError:
        point_estimate, lower, upper, confidence, attribution = _naive_forecast(features)

    target_date = (datetime.now(UTC) + timedelta(days=horizon_days)).date()

    return Forecast(
        forecast_type="rate_change_pct",
        entity_type="lane",
        entity_id=lane_id,
        generated_at=datetime.now(UTC),
        target_date=target_date,
        horizon_days=horizon_days,
        predicted_value=point_estimate,
        unit="pct_change",
        lower_bound=lower,
        upper_bound=upper,
        confidence=confidence,
        model_version=MODEL_VERSION,
        signal_attribution=attribution,
    )


def _naive_forecast(features: pd.DataFrame) -> tuple[float, float, float, float, list]:
    """
    Fallback forecast used before a trained model exists for a lane:
    "no change predicted", wide confidence band, low confidence score.

    This is intentionally conservative — it's better to tell an early
    customer "we don't have enough signal yet" (low confidence, ~0.3-0.4)
    than to fabricate a confident-looking number.
    """
    return 0.0, -5.0, 5.0, 0.35, [{"signal_id": "baseline", "contribution": 1.0, "note": "naive fallback — model not yet trained"}]


def _confidence_from_spread(lower: float, upper: float) -> float:
    """
    Translate the width of the [10th, 90th] percentile prediction
    interval into a 0-1 confidence score. Narrower interval = higher
    confidence. Calibration constants here are starting points —
    revisit once real forecast/outcome pairs accumulate (see
    app/services/forecasting.py validation loop).
    """
    spread = abs(upper - lower)
    confidence = max(0.3, min(0.95, 1 - (spread / 40)))
    return round(confidence, 2)


def _compute_attribution(features: pd.DataFrame) -> list[dict]:
    """
    Lightweight signal attribution: report the most recent value of each
    input signal alongside its 30-day average, so the dashboard can show
    "here's what the model is looking at and how it compares to normal."

    A more rigorous approach (SHAP values) can replace this once models
    are trained on real data — the *shape* of the output
    (list of {signal_id, value, baseline, ...}) is what the frontend and
    Forecast.signal_attribution field expect, so SHAP-based attribution
    can be a drop-in upgrade.
    """
    latest = features.iloc[-1]
    attribution = []

    for signal_id in FORECAST_INPUT_SIGNALS:
        if signal_id not in features.columns:
            continue
        baseline_col = f"{signal_id}_30d_avg"
        attribution.append({
            "signal_id": signal_id,
            "value": float(latest[signal_id]),
            "baseline_30d": float(latest[baseline_col]) if baseline_col in features.columns else None,
        })

    return attribution
