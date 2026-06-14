"""Pydantic schemas for auth, users, and organizations."""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.organization import SubscriptionTier


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    organization_name: str
    """
    New users create a new organization at signup. Inviting additional
    users to an existing org (for Pro's 5-seat tier etc.) is a separate
    endpoint — see app/api/v1/routes/organizations.py.
    """


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_org_admin: bool
    organization_id: uuid.UUID


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: SubscriptionTier
    is_active: bool
    lane_limit: int | None
