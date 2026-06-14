"""
Auth routes: registration and login.

Registration creates both a new Organization and its first User
(who becomes org admin) — see UserCreate schema docstring for why
org creation is bundled with signup rather than a separate step.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.organization import Organization, Subscription, SubscriptionTier, User
from app.schemas.auth import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    org = Organization(name=payload.organization_name)
    db.add(org)
    db.flush()  # populate org.id before using it below

    # New orgs start on Core tier with a 3-lane limit, matching the
    # pricing structure in the business plan. Upgrades happen via Stripe
    # webhooks updating this row (see app/api/v1/routes/billing.py).
    subscription = Subscription(organization_id=org.id, tier=SubscriptionTier.CORE, lane_limit=3)
    db.add(subscription)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        organization_id=org.id,
        is_org_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)
