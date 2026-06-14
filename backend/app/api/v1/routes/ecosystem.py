"""
Ecosystem data routes.

Two distinct endpoints reflecting the hard boundary described in
app/models/ecosystem.py:

  - POST /ecosystem/submit  — orgs submit raw operational data
    (any tier with a signed data-sharing agreement)
  - GET  /ecosystem/benchmarks — orgs read anonymized aggregate
    benchmarks (Enterprise+ only)

These never touch the same rows: submissions write to
EcosystemDataSubmission, benchmarks read from EcosystemBenchmark
(populated by the scheduled aggregation job in
app/services/ecosystem.py).
"""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_organization, require_tier
from app.db.session import get_db
from app.models.ecosystem import EcosystemBenchmark, EcosystemDataSubmission
from app.models.organization import Organization, SubscriptionTier

router = APIRouter(prefix="/ecosystem", tags=["ecosystem"])


class EcosystemSubmission(BaseModel):
    data_type: str  # e.g. "booking_velocity", "lane_utilization"
    lane_id: str | None = None
    period_start: date
    period_end: date
    value: float
    unit: str
    raw_payload: dict = {}


class BenchmarkRead(BaseModel):
    data_type: str
    lane_id: str | None
    period_start: date
    period_end: date
    median_value: float
    p25_value: float
    p75_value: float
    unit: str
    contributor_count: int

    model_config = ConfigDict(from_attributes=True)


@router.post("/submit", status_code=201)
def submit_ecosystem_data(
    payload: EcosystemSubmission,
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    """
    Accepts a single data point under the org's ecosystem data
    agreement. At MVP this is the API equivalent of the CSV upload
    flow — same destination table either way.

    NOTE: this endpoint intentionally does NOT check subscription tier.
    Ecosystem data contribution is part of onboarding for *all* tiers
    (it's how the network effect bootstraps) — only *reading* aggregate
    benchmarks is tier-gated, below.
    """
    submission = EcosystemDataSubmission(organization_id=org.id, **payload.model_dump())
    db.add(submission)
    db.commit()
    return {"status": "received"}


@router.get("/benchmarks", response_model=list[BenchmarkRead])
def get_benchmarks(
    data_type: str | None = None,
    lane_id: str | None = None,
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
    _: None = Depends(require_tier(SubscriptionTier.ENTERPRISE)),
):
    """
    Returns anonymized peer benchmarks. Enterprise+ only (per pricing
    tiers — Pro can add this as a paid add-on later, at which point this
    dependency becomes a feature-flag check rather than a hard tier
    gate).
    """
    query = db.query(EcosystemBenchmark)
    if data_type:
        query = query.filter(EcosystemBenchmark.data_type == data_type)
    if lane_id:
        query = query.filter(EcosystemBenchmark.lane_id == lane_id)

    return query.order_by(EcosystemBenchmark.period_end.desc()).limit(50).all()
