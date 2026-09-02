from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class PartnerInviteCreateRequest(BaseModel):
    email: str
    note: Optional[str] = None  # e.g. "CSC201 course rep"


class PartnerInviteResponse(BaseModel):
    id: int
    code: str
    email: str 
    note: Optional[str] = None
    used_by_email: Optional[str] = None
    used_at: Optional[datetime] = None
    email_sent: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PartnerResponse(BaseModel):
    id: int
    user_email: str
    referral_code: Optional[str] = None
    status: str
    invitee_count: int
    total_earnings: int
    created_at: datetime

    class Config:
        from_attributes = True


class PayoutRequestResponse(BaseModel):
    id: int
    partner_id: int
    partner_email: Optional[str] = None
    amount_naira: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayoutRequestBody(BaseModel):
    amount_naira: int

class PartnerEarningResponse(BaseModel):
    id: int
    source_user_id: int
    payment_reference: str
    amount_naira: int
    available_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class PartnerPayoutRequestResponse(BaseModel):
    id: int
    amount_naira: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True