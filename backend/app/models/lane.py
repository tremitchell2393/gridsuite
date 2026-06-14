"""
Lane watchlists and alert configuration.

A "lane" is the primary entity customers care about (e.g. "SHSE-LAX").
Organizations watch lanes (gated by subscription tier's lane_limit) and
configure alerts on signals/forecasts for those lanes.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import PortableUUID as UUID


class WatchedLane(Base):
    """A lane an organization is tracking on their dashboard."""
    __tablename__ = "watched_lanes"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("organizations.id"), nullable=False, index=True)

    lane_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "SHSE-LAX"
    label: Mapped[str] = mapped_column(String(100), nullable=True)     # optional friendly name

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertChannel(str, enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class AlertCondition(str, enum.Enum):
    FORECAST_CHANGE_ABOVE = "forecast_change_above"   # |predicted change| > threshold
    SIGNAL_THRESHOLD = "signal_threshold"              # signal value crosses threshold
    CONFIDENCE_ABOVE = "confidence_above"              # forecast confidence > threshold


class AlertRule(Base):
    """
    A customer-configured alert: "notify me via X when Y crosses Z for lane W."

    Evaluated by the alerting engine (app/services/alerting.py) after each
    daily signal/forecast update.
    """
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("organizations.id"), nullable=False, index=True)

    lane_id: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_or_forecast_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "rate_change_pct" or "customs_velocity_index"

    condition: Mapped[AlertCondition] = mapped_column(
        Enum(AlertCondition, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    threshold: Mapped[float] = mapped_column(Float, nullable=False)

    channel: Mapped[AlertChannel] = mapped_column(
        Enum(AlertChannel, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    destination: Mapped[str] = mapped_column(String(500), nullable=False)
    # email address, Slack webhook URL, or generic webhook URL depending on channel

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
