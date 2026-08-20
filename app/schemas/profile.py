# app/schemas/profile.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProfileResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)