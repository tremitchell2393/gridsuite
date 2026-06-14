"""
Alerting service — evaluates customer-configured AlertRules against
the latest signals/forecasts and fires notifications.

Run after the daily ingestion + forecasting jobs complete (see
app/services/scheduler.py for ordering).
"""
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.forecast import Forecast
from app.models.lane import AlertChannel, AlertCondition, AlertRule
from app.models.signal import Signal

logger = logging.getLogger(__name__)


def evaluate_all_alerts() -> int:
    """Evaluate every active alert rule. Returns count of alerts fired."""
    db = SessionLocal()
    fired = 0

    try:
        rules = db.execute(select(AlertRule).where(AlertRule.is_active == True)).scalars().all()  # noqa: E712

        for rule in rules:
            current_value = _get_current_value(db, rule)
            if current_value is None:
                continue

            if _condition_met(rule, current_value):
                _fire_alert(rule, current_value)
                rule.last_triggered_at = datetime.now(UTC)
                fired += 1

        db.commit()
    finally:
        db.close()

    logger.info("Alert evaluation complete: %d alerts fired", fired)
    return fired


def _get_current_value(db: Session, rule: AlertRule) -> float | None:
    """
    Fetch the latest value for whatever this rule monitors — either a
    raw signal or a forecast, depending on `signal_or_forecast_type`.
    """
    # Try forecasts first (e.g. "rate_change_pct")
    forecast_stmt = (
        select(Forecast)
        .where(
            Forecast.entity_type == "lane",
            Forecast.entity_id == rule.lane_id,
            Forecast.forecast_type == rule.signal_or_forecast_type,
        )
        .order_by(Forecast.generated_at.desc())
        .limit(1)
    )
    forecast = db.execute(forecast_stmt).scalar_one_or_none()
    if forecast:
        if rule.condition == AlertCondition.CONFIDENCE_ABOVE:
            return forecast.confidence
        return forecast.predicted_value

    # Fall back to raw signals (e.g. "customs_velocity_index")
    signal_stmt = (
        select(Signal)
        .where(
            Signal.entity_id == rule.lane_id,
            Signal.signal_id == rule.signal_or_forecast_type,
        )
        .order_by(Signal.timestamp.desc())
        .limit(1)
    )
    signal = db.execute(signal_stmt).scalar_one_or_none()
    return signal.value if signal else None


def _condition_met(rule: AlertRule, value: float) -> bool:
    if rule.condition == AlertCondition.FORECAST_CHANGE_ABOVE:
        # `value` here is Forecast.predicted_value, stored as a fraction
        # (e.g. 0.1129 = +11.29%). Thresholds are entered by users in
        # percentage points (e.g. "12" meaning 12%), matching the
        # dashboard's display format — so compare against value*100.
        return abs(value * 100) > rule.threshold
    if rule.condition == AlertCondition.SIGNAL_THRESHOLD:
        return value > rule.threshold
    if rule.condition == AlertCondition.CONFIDENCE_ABOVE:
        return value > rule.threshold
    return False


def _fire_alert(rule: AlertRule, value: float) -> None:
    display_value = f"{value * 100:.1f}%" if rule.condition == AlertCondition.FORECAST_CHANGE_ABOVE else value
    message = (
        f"GridSuite Alert — {rule.lane_id}: {rule.signal_or_forecast_type} "
        f"is {display_value} (threshold: {rule.threshold})"
    )

    try:
        if rule.channel == AlertChannel.EMAIL:
            _send_email(rule.destination, message)
        elif rule.channel == AlertChannel.SLACK:
            _post_webhook(rule.destination, {"text": message})
        elif rule.channel == AlertChannel.WEBHOOK:
            _post_webhook(rule.destination, {"lane_id": rule.lane_id, "metric": rule.signal_or_forecast_type, "value": value, "message": message})
    except Exception:
        logger.exception("Failed to send alert for rule %s", rule.id)


def _send_email(to_address: str, message: str) -> None:
    """
    Stub — wire up to Postmark/SendGrid per the architecture doc.
    Logging instead of raising NotImplementedError so alert evaluation
    doesn't crash before email is wired up.
    """
    logger.info("[EMAIL STUB] to=%s message=%s", to_address, message)


def _post_webhook(url: str, payload: dict) -> None:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
