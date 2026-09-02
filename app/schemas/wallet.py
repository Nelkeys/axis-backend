from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class WalletSummaryResponse(BaseModel):
    referral_code: str
    
    # Stats for everyone
    invitee_count: int
    
    # Normal user stats
    coin_balance: int
    
    # Partner stats
    is_partner: bool
    partner_available_cash: int
    partner_pending_cash: int 


class CoinEntryResponse(BaseModel):
    id: int
    amount: int   
    type: str     
    reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CoinHistoryResponse(BaseModel):
    balance: int
    entries: List[CoinEntryResponse]



class InviteeResponse(BaseModel):
    id: int
    email: str
    joined_at: datetime
    has_paid: bool
    earned_from_them: int = 0

    class Config:
        from_attributes = True