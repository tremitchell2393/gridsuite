"""
The Forecast model — output of the modeling engine.

Forecasts are computed in batch (see app/modeling/) and written here.
The API reads pre-computed forecasts rather than running models
on-demand, keeping request latency independent of model complexity.

Each forecast row also carries `signal_attribution` — a record of which
input signals most influenced this prediction. This isn't a nice-to-have:
it's central to the brand's "we state, we don't sell" trust proposition.
Customers should always be able to see *why* the model is calling
something.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import PortableJSON


class Forecast(Base):
    """
    A single forecast: a prediction for a metric on a given entity,
    for a target date, made at a given point in time.
    """
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # What's being forecast (e.g. "rate_change_pct")
    forecast_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # What entity this forecast is for
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g. "lane" / "SHSE-LAX"

    # When this forecast was generated (model run date)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # The future date this forecast is FOR (e.g. generated_at + 30 days)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Forecast horizon in days (30/60/90) — denormalized for easy filtering
    horizon_days: Mapped[int] = mapped_column(nullable=False)

    # The prediction itself
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    # Confidence interval (from quantile regression — see app/modeling/)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=True)

    # Overall confidence score (0-1) shown to customers
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Which model version produced this (ties to MLflow run ID)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)

    # Signal attribution: which input signals drove this forecast and how
    # much. Shape: [{"signal_id": "...", "contribution": 0.34, "value": ...}, ...]
    signal_attribution: Mapped[list] = mapped_column(PortableJSON, nullable=False, default=list)

    # Filled in once target_date has passed — used for the accuracy dashboard
    # and model retraining feedback loop.
    realized_value: Mapped[float] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_forecasts_lookup", "forecast_type", "entity_type", "entity_id", "target_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Forecast {self.forecast_type} {self.entity_type}:{self.entity_id} "
            f"-> {self.target_date} = {self.predicted_value}{self.unit} "
            f"(conf={self.confidence})>"
        )
