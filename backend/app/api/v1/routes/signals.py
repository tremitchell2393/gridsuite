"""
Signal routes.

Read-only endpoints over the Signal Store. The internal dashboard and
the external API (Pro+, see require_tier) share these same endpoints —
external API access is just the same routes reached with an API key
instead of a session token (API key auth to be added alongside Stripe
billing in app/api/v1/routes/billing.py).
"""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.signal import Signal
from app.schemas.signal import SignalListResponse, SignalRead

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalListResponse)
def list_signals(
    entity_type: str = Query(..., description='e.g. "lane", "port", "carrier"'),
    entity_id: str = Query(..., description='e.g. "SHSE-LAX"'),
    signal_id: str | None = Query(None, description="Filter to a single signal type"),
    days: int = Query(30, ge=1, le=365, description="How many days of history to return"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    List signal observations for a given entity over a time window.

    This is the primary read endpoint the dashboard uses to populate
    charts (e.g. "show me customs_velocity_index for lane SHSE-LAX over
    the last 30 days").
    """
    since = datetime.now(UTC) - timedelta(days=days)

    stmt = select(Signal).where(
        Signal.entity_type == entity_type,
        Signal.entity_id == entity_id,
        Signal.timestamp >= since,
    )
    if signal_id:
        stmt = stmt.where(Signal.signal_id == signal_id)

    stmt = stmt.order_by(Signal.timestamp.asc())

    rows = db.execute(stmt).scalars().all()

    return SignalListResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        signals=[SignalRead.from_orm_with_metadata(r) for r in rows],
    )


@router.get("/library", response_model=list[str])
def list_available_signals(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """
    Returns the distinct list of signal_ids currently in the Signal
    Store — powers the "Signal Library" page (browsable list of active
    signals, per the architecture doc's MVP screen list).
    """
    stmt = select(Signal.signal_id).distinct()
    return [row[0] for row in db.execute(stmt).all()]
