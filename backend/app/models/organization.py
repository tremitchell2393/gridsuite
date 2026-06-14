"""
Multi-tenant core: Organizations, Users, and Subscriptions.

Even at MVP, every user belongs to an Organization (a customer account
may have multiple users — this is baked into the pricing tiers from day
one, e.g. "Pro: 5 user seats"). API keys and ecosystem data agreements
are scoped to the Organization, not individual users.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import PortableUUID as UUID


class SubscriptionTier(str, enum.Enum):
    CORE = "core"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    INSTITUTIONAL = "institutional"


class Organization(Base):
    """A customer account. Owns users, subscriptions, API keys, lane
    watchlists, alert configs, and ecosystem data agreements."""
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Stripe customer ID — links to billing
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="organization", uselist=False
    )
    watched_lanes: Mapped[list["WatchedLane"]] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("organizations.id"), nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="users")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_org_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    """
    One subscription per organization, tracking tier and Stripe state.

    Tier gates feature access (see app/api/v1/deps.py for the
    `require_tier` dependency used on Pro/Enterprise-only routes).
    """
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("organizations.id"), nullable=False, unique=True
    )
    organization: Mapped["Organization"] = relationship(back_populates="subscription")

    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, values_callable=lambda e: [m.value for m in e]),
        nullable=False, default=SubscriptionTier.CORE
    )

    # Stripe subscription ID — None if no active paid subscription (e.g. trial)
    stripe_subscription_id: Mapped[str] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Lane coverage limit — Core: 3, Pro: 15, Enterprise/Institutional: unlimited (None)
    lane_limit: Mapped[int] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=datetime.utcnow
    )
