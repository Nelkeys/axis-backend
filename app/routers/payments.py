# app/routers/payments.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.payment import PaymentInitRequest, PaymentInitResponse
from app.services.payment_service import get_payment_amount, initialize_paystack_transaction

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initialize", response_model=PaymentInitResponse)
async def initialize_payment(
    data: PaymentInitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """user clicks 'Buy' → returns Paystack checkout URL."""

    # 1. Determine price server-side (never trust frontend)
    amount = get_payment_amount(db, current_user.id, data.course_id, data.action_type)

    # 2. Call Paystack
    result = await initialize_paystack_transaction(
        email=current_user.email,
        amount_naira=amount,
        metadata={
            "user_id": current_user.id,
            "course_id": data.course_id,
            "action_type": data.action_type,
        },
    )

    return PaymentInitResponse(
        authorization_url=result["authorization_url"],
        reference=result["reference"],
    )