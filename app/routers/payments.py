from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.payment import PaymentInitRequest, PaymentInitResponse
from app.services.payment_service import get_payment_amount, initialize_paystack_transaction
from app.services.referral_service import get_coin_balance

router = APIRouter(prefix="/payments", tags=["Payments"])

COIN_SPEND_CAP = 0.5  # coins can cover at most 50% of the price


@router.post("/initialize", response_model=PaymentInitResponse)
async def initialize_payment(
    data: PaymentInitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """user clicks 'Buy' → returns Paystack checkout URL."""

    # 1. Determine price server-side (never trust frontend)
    base_amount = get_payment_amount(db, current_user.id, data.course_id, data.action_type)

    # 2. Apply coin discount (validated server-side)
    coins_to_apply = data.coins_to_apply or 0
    coin_discount = 0

    if coins_to_apply > 0:
        balance = get_coin_balance(db, current_user.id)
        if coins_to_apply > balance:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient coins. You have {balance}, tried to apply {coins_to_apply}.",
            )
        # Cap coin spend at 50% of the course price
        max_coin_spend = int(base_amount * COIN_SPEND_CAP)
        coin_discount = min(coins_to_apply, max_coin_spend)

    amount_to_charge = base_amount - coin_discount

    # Paystack needs a sane minimum (avoid tiny/zero charges)
    if amount_to_charge < 100:
        raise HTTPException(
            status_code=400,
            detail="Amount after coin discount is too low to process.",
        )

    # 3. Call Paystack with the discounted amount
    result = await initialize_paystack_transaction(
        email=current_user.email,
        amount_naira=amount_to_charge,
        metadata={
            "user_id": current_user.id,
            "course_id": data.course_id,
            "action_type": data.action_type,
            "coins_applied": coin_discount,  # webhook uses this to deduct coins
        },
    )

    return PaymentInitResponse(
        authorization_url=result["authorization_url"],
        reference=result["reference"],
        amount_charged=amount_to_charge,
        coins_applied=coin_discount,
    )