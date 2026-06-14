"""
Tests for the alerting engine.

Covers `_condition_met`'s unit handling — this is the one place where a
silent bug would mean alerts simply never fire (or fire on every run),
which is hard for a user to notice on their own. The
FORECAST_CHANGE_ABOVE case is the trickiest: Forecast.predicted_value
is stored as a fraction (0.1129 = +11.29%), but users enter thresholds
in percentage points (e.g. "12" meaning 12%) to match the dashboard's
display format.
"""
from app.models.lane import AlertCondition, AlertChannel, AlertRule
from app.services.alerting import _condition_met


def _make_rule(condition: AlertCondition, threshold: float) -> AlertRule:
    return AlertRule(
        organization_id="00000000-0000-0000-0000-000000000000",
        lane_id="SHSE-LAX",
        signal_or_forecast_type="rate_change_pct",
        condition=condition,
        threshold=threshold,
        channel=AlertChannel.EMAIL,
        destination="ops@example.com",
    )


def test_forecast_change_above_does_not_fire_below_threshold():
    """11.29% forecast vs threshold of 12 (percentage points) -> no fire."""
    rule = _make_rule(AlertCondition.FORECAST_CHANGE_ABOVE, threshold=12)
    assert _condition_met(rule, value=0.1129) is False


def test_forecast_change_above_fires_above_threshold():
    """13.58% forecast vs threshold of 10 (percentage points) -> fires."""
    rule = _make_rule(AlertCondition.FORECAST_CHANGE_ABOVE, threshold=10)
    assert _condition_met(rule, value=0.1358) is True


def test_forecast_change_above_handles_negative_forecasts():
    """A -15% forecast vs threshold of 10 should still fire (abs value)."""
    rule = _make_rule(AlertCondition.FORECAST_CHANGE_ABOVE, threshold=10)
    assert _condition_met(rule, value=-0.15) is True


def test_signal_threshold_compares_raw_value():
    """SIGNAL_THRESHOLD compares the raw signal value directly (no %
    conversion) — e.g. customs_velocity_index > 1.15."""
    rule = _make_rule(AlertCondition.SIGNAL_THRESHOLD, threshold=1.15)
    assert _condition_met(rule, value=1.18) is True
    assert _condition_met(rule, value=1.10) is False


def test_confidence_above_compares_raw_value():
    rule = _make_rule(AlertCondition.CONFIDENCE_ABOVE, threshold=0.8)
    assert _condition_met(rule, value=0.85) is True
    assert _condition_met(rule, value=0.77) is False
