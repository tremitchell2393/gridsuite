"""
Shared FastAPI dependencies: current-user resolution and subscription
tier gating.

`require_tier` is how Pro/Enterprise-only features (full API access,
ecosystem benchmarking, etc.) are gated — per the architecture doc,
tier gates feature access at the API layer based on the org's
Subscription.tier.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.organization import Organization, Subscription, SubscriptionTier, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_current_organization(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    org = db.get(Organization, user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# Tier ordering — used to check "at least this tier"
_TIER_ORDER = {
    SubscriptionTier.CORE: 0,
    SubscriptionTier.PRO: 1,
    SubscriptionTier.ENTERPRISE: 2,
    SubscriptionTier.INSTITUTIONAL: 3,
}


def require_tier(minimum_tier: SubscriptionTier):
    """
    Dependency factory: returns a dependency that raises 403 unless the
    current user's organization has an active subscription at
    `minimum_tier` or higher.

    Usage:
        @router.get("/ecosystem/benchmarks")
        def get_benchmarks(
            org: Organization = Depends(get_current_organization),
            _: None = Depends(require_tier(SubscriptionTier.ENTERPRISE)),
        ):
            ...
    """

    def dependency(
        org: Annotated[Organization, Depends(get_current_organization)],
        db: Annotated[Session, Depends(get_db)],
    ) -> None:
        subscription = db.get(Subscription, org.id) if org.subscription is None else org.subscription

        if subscription is None or not subscription.is_active:
            raise HTTPException(status_code=403, detail="Active subscription required")

        if _TIER_ORDER[subscription.tier] < _TIER_ORDER[minimum_tier]:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires the {minimum_tier.value} tier or higher",
            )

    return dependency
