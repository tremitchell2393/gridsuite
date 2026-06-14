"""
Tests for the modeling layer.

At this stage (no trained models exist yet), `predict_for_lane` should
fall back to the naive forecast — this test locks in that behavior so
the dashboard always has *something* to show, with appropriately low
confidence, before real models are trained.
"""
from datetime import datetime, timezone

from app.modeling.rate_forecast import _naive_forecast, predict_for_lane
from app.models.signal import Signal


def test_naive_forecast_shape():
    point, lower, upper, confidence, attribution = _naive_forecast(features=None)

    assert point == 0.0
    assert lower < 0 < upper
    assert 0.0 <= confidence <= 1.0
    assert confidence < 0.5  # naive forecasts should signal low confidence
    assert attribution[0]["signal_id"] == "baseline"


def test_predict_for_lane_falls_back_to_naive_without_trained_model(db_session):
    """
    With signal data present but no trained model file on disk,
    predict_for_lane should return a Forecast using the naive fallback
    rather than raising.
    """
    now = datetime.now(timezone.utc)

    db_session.add(
        Signal(
            signal_id="customs_velocity_index",
            entity_type="lane",
            entity_id="SHSE-LAX",
            timestamp=now,
            value=1.18,
            unit="ratio_to_30d_avg",
            source="customs_velocity",
            confidence=1.0,
            metadata_json={},
        )
    )
    db_session.commit()

    forecast = predict_for_lane(db_session, "SHSE-LAX", horizon_days=30)

    assert forecast is not None
    assert forecast.entity_id == "SHSE-LAX"
    assert forecast.horizon_days == 30
    assert forecast.confidence < 0.5
    assert forecast.signal_attribution[0]["signal_id"] == "baseline"


def test_predict_for_lane_returns_none_without_any_signals(db_session):
    """No signal history at all -> no forecast, not an error."""
    forecast = predict_for_lane(db_session, "UNKNOWN-LANE", horizon_days=30)
    assert forecast is None
