"""
The Signal model — the architectural core of GridSuite.

Every piece of data GridSuite ingests, regardless of source (AIS, customs
filings, carrier rates, weather, ecosystem data, etc.), is normalized into
this single schema before it touches any downstream logic.

WHY THIS MATTERS:
The modeling layer, API, and dashboard never need to know where a signal
came from. They query signals by (signal_id, entity_type, entity_id, time
range). Adding a new data source means writing one adapter (see
app/ingestion/adapters/) that outputs rows in this shape — nothing else
in the system changes.

See the Technical Architecture doc, section 3, for the full rationale.

NOTE ON TIMESCALE:
In production this table should be converted to a TimescaleDB hypertable,
partitioned on `timestamp`. That's a post-migration step
(`SELECT create_hypertable('signals', 'timestamp')`) — the ORM model below
is unaffected either way, so we keep this as a plain SQLAlchemy model and
note the Timescale conversion in the migration that creates this table.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import PortableJSON


class Signal(Base):
    """
    A single observation of a named metric for a specific entity at a
    specific point in time.

    Examples:
      - signal_id="customs_velocity_index", entity_type="lane",
        entity_id="SHSE-LAX", value=1.18, unit="ratio_to_30d_avg"
      - signal_id="port_dwell_time", entity_type="port",
        entity_id="SHSE", value=4.2, unit="days"
      - signal_id="ais_route_deviation", entity_type="vessel",
        entity_id="IMO9839278", value=1.0, unit="boolean_flag"
    """
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # What metric this is (e.g. "customs_velocity_index", "port_dwell_time")
    signal_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # What this signal is about
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # "lane" | "port" | "carrier" | "vessel" | "country" | ...
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g. "SHSE-LAX", "PORT_SHSE", "COSCO", "IMO9839278"

    # When the underlying event/observation occurred (not when we ingested it)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # The actual value and its unit
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "pct_change", "usd_per_feu", "days", "boolean_flag", "ratio_to_30d_avg"

    # Which ingestion adapter produced this (for debugging / reprocessing)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. "ais_marinetraffic", "customs_census", "freightos_index"

    # Data quality score for THIS OBSERVATION (0-1) — distinct from a
    # forecast's confidence score. Reflects e.g. how complete/fresh the
    # source data was when this row was produced.
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Source-specific extra fields that don't fit the core schema
    # (e.g. vessel name, HS code, raw API response excerpt)
    metadata_json: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)

    # When this row was written (for auditing/debugging ingestion delays)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # The query pattern that matters most: "give me all values of
        # signal X for entity Y over time range Z"
        Index("ix_signals_lookup", "signal_id", "entity_type", "entity_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<Signal {self.signal_id} {self.entity_type}:{self.entity_id} "
            f"@ {self.timestamp.isoformat()} = {self.value}{self.unit}>"
        )
