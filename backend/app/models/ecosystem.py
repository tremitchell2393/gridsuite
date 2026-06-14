"""
Ecosystem Data models.

This module implements the "hard architectural boundary" principle from
the Technical Architecture doc (section 9, principle 4): raw customer-
submitted data is stored separately and is NEVER directly queryable by
the benchmarking/signal layers. Only aggregated outputs (computed by a
scheduled job — see app/services/ecosystem.py) are exposed.

Flow:
  1. Org submits raw data -> EcosystemDataSubmission (raw, org-scoped, private)
  2. Scheduled job aggregates across orgs -> EcosystemBenchmark (anonymized, shared)
  3. API serves EcosystemBenchmark rows to Enterprise+ customers; never (1).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import PortableJSON
from app.db.types import PortableUUID as UUID


class EcosystemDataSubmission(Base):
    """
    Raw data submitted by a customer org under their ecosystem data
    agreement (e.g. booking velocity, lane utilization, carrier
    performance).

    ACCESS CONTROL: this table must never be joined into any query that
    returns data to a different organization, and must never feed
    directly into the `signals` table. Only the aggregation job
    (app/services/ecosystem.py) reads from here, and it writes only
    aggregate statistics to EcosystemBenchmark below.
    """
    __tablename__ = "ecosystem_data_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("organizations.id"), nullable=False, index=True)

    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "booking_velocity", "lane_utilization", "carrier_performance"

    lane_id: Mapped[str] = mapped_column(String(50), nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    raw_payload: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    # original submitted data, for audit purposes only

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EcosystemBenchmark(Base):
    """
    Anonymized, aggregated peer benchmarks — the customer-facing output
    of the ecosystem data network.

    Written ONLY by the scheduled aggregation job. Requires a minimum
    number of contributing organizations (enforced in
    app/services/ecosystem.py) before a benchmark is published, to
    prevent any single contributor's data from being inferable.
    """
    __tablename__ = "ecosystem_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    data_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    lane_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Aggregate stats only — never individual values
    median_value: Mapped[float] = mapped_column(Float, nullable=False)
    p25_value: Mapped[float] = mapped_column(Float, nullable=False)
    p75_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    contributor_count: Mapped[int] = mapped_column(nullable=False)
    # Enforced minimum (e.g. >= 5) before this row is created — see
    # MIN_CONTRIBUTORS_FOR_BENCHMARK in app/services/ecosystem.py

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
