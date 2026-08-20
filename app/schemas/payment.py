from pydantic import BaseModel
from typing import Literal


class PaymentInitRequest(BaseModel):
    course_id: int
    action_type: Literal["new", "renew", "repurchase"]


class PaymentInitResponse(BaseModel):
    authorization_url: str
    reference: str