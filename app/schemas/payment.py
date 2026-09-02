from pydantic import BaseModel, Field
from typing import Literal


class PaymentInitRequest(BaseModel):
    course_id: int
    action_type: Literal["new", "renew", "repurchase"]
    coins_to_apply: int = Field(default=0, ge=0) 


class PaymentInitResponse(BaseModel):
    authorization_url: str
    reference: str
    amount_charged: int 
    coins_applied: int 