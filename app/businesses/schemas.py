from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.businesses.models import MembershipRole


class BusinessBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class BusinessRead(BaseModel):
    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MembershipBase(BaseModel):
    role: MembershipRole = MembershipRole.STAFF


class MembershipCreate(MembershipBase):
    user_id: int


class MembershipRead(BaseModel):
    user_id: int
    business_id: int
    role: MembershipRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessWithMemberships(BaseModel):
    id: int
    name: str
    slug: str
    memberships: list[MembershipRead] = []

    model_config = ConfigDict(from_attributes=True)
