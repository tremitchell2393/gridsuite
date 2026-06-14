"""
Alert rule routes — CRUD for customer-configured alerts.

Rules are evaluated by the alerting engine (app/services/alerting.py)
after each daily signal/forecast update. Slack/webhook channels are
Pro+ — gated via require_tier.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_organization, require_tier
from app.db.session import get_db
from app.models.lane import AlertChannel, AlertCondition, AlertRule
from app.models.organization import Organization, SubscriptionTier

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleCreate(BaseModel):
    lane_id: str
    signal_or_forecast_type: str
    condition: AlertCondition
    threshold: float
    channel: AlertChannel
    destination: str


class AlertRuleRead(BaseModel):
    id: uuid.UUID
    lane_id: str
    signal_or_forecast_type: str
    condition: AlertCondition
    threshold: float
    channel: AlertChannel
    destination: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[AlertRuleRead])
def list_alert_rules(
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    return db.query(AlertRule).filter(AlertRule.organization_id == org.id).all()


@router.post("", response_model=AlertRuleRead, status_code=201)
def create_alert_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    # Email alerts are available at all tiers; Slack/webhook are Pro+.
    if payload.channel in (AlertChannel.SLACK, AlertChannel.WEBHOOK):
        require_tier(SubscriptionTier.PRO)(org=org, db=db)

    rule = AlertRule(organization_id=org.id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_alert_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    rule = (
        db.query(AlertRule)
        .filter(AlertRule.organization_id == org.id, AlertRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    db.delete(rule)
    db.commit()
