"""
Lane watchlist routes — manage which lanes an org tracks on their
dashboard. Enforces the subscription tier's lane_limit (Core: 3,
Pro: 15, Enterprise/Institutional: unlimited).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_organization
from app.db.session import get_db
from app.models.lane import WatchedLane
from app.models.organization import Organization

router = APIRouter(prefix="/lanes", tags=["lanes"])


class WatchedLaneCreate(BaseModel):
    lane_id: str
    label: str | None = None


class WatchedLaneRead(BaseModel):
    lane_id: str
    label: str | None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[WatchedLaneRead])
def list_watched_lanes(
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    return db.query(WatchedLane).filter(WatchedLane.organization_id == org.id).all()


@router.post("", response_model=WatchedLaneRead, status_code=201)
def add_watched_lane(
    payload: WatchedLaneCreate,
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    current_count = db.query(WatchedLane).filter(WatchedLane.organization_id == org.id).count()

    lane_limit = org.subscription.lane_limit if org.subscription else 3
    if lane_limit is not None and current_count >= lane_limit:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Lane limit reached ({lane_limit}) for your current plan. "
                "Upgrade your subscription to track more lanes."
            ),
        )

    lane = WatchedLane(organization_id=org.id, lane_id=payload.lane_id, label=payload.label)
    db.add(lane)
    db.commit()
    db.refresh(lane)
    return lane


@router.delete("/{lane_id}", status_code=204)
def remove_watched_lane(
    lane_id: str,
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    lane = (
        db.query(WatchedLane)
        .filter(WatchedLane.organization_id == org.id, WatchedLane.lane_id == lane_id)
        .first()
    )
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found in watchlist")

    db.delete(lane)
    db.commit()
