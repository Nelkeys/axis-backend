from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.core.rate_limiter import limiter

from app.database import get_db
from app.models.user import User
from app.models.referral import Partner, PartnerInvite, PartnerEarning, PayoutRequest
from app.core.dependencies import get_current_user
from app.services.referral_service import calculate_partner_balance
from app.schemas.referral import (
    PayoutRequestBody,
    PartnerEarningResponse,
    PartnerPayoutRequestResponse,
)

router = APIRouter(prefix="/partner", tags=["Partner"])

MIN_PAYOUT = 1000  # ₦1,000 minimum withdrawal


def _get_active_partner(db: Session, user_id: int) -> Partner:
    """Helper: returns the active partner or raises 403."""
    partner = db.query(Partner).filter(
        Partner.user_id == user_id,
        Partner.status == "ACTIVE",
    ).first()
    if not partner:
        raise HTTPException(status_code=403, detail="You are not an active partner")
    return partner


@router.get("/me")
def get_partner_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    partner = db.query(Partner).filter(Partner.user_id == current_user.id).first()
    return {
        "is_partner": bool(partner and partner.status == "ACTIVE"),
        "status": partner.status if partner else None,
    }


@router.post("/redeem")
@limiter.limit("5/minute")
def redeem_partner_invite(
    request: Request,
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite = db.query(PartnerInvite).filter(PartnerInvite.code == code.strip().upper()).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Only the email the invite was created for can redeem it
    if invite.email != current_user.email:
        raise HTTPException(
            status_code=403,
            detail="This invite code was generated for a different email address.",
        )

    if invite.used_by_user_id:
        raise HTTPException(status_code=400, detail="This invite code has already been used")

    partner = db.query(Partner).filter(Partner.user_id == current_user.id).first()

    if partner and partner.status == "ACTIVE":
        raise HTTPException(status_code=400, detail="You are already an active partner")

    if partner:
        # Previously revoked — a fresh code reactivates them.
        partner.status = "ACTIVE"
    else:
        partner = Partner(user_id=current_user.id, status="ACTIVE")
        db.add(partner)

    invite.used_by_user_id = current_user.id
    invite.used_at = datetime.now(timezone.utc)

    db.commit()
    return {"status": "partner", "message": "Welcome! You are now a partner."}


@router.get("/earnings", response_model=List[PartnerEarningResponse])
def get_my_earnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all commission entries for this partner, newest first."""
    partner = _get_active_partner(db, current_user.id)
    earnings = (
        db.query(PartnerEarning)
        .filter(PartnerEarning.partner_id == partner.id)
        .order_by(PartnerEarning.created_at.desc())
        .all()
    )
    return earnings


@router.get("/payout-requests", response_model=List[PartnerPayoutRequestResponse])
def get_my_payout_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Payout request history for this partner."""
    partner = _get_active_partner(db, current_user.id)
    payout_history = (
        db.query(PayoutRequest)
        .filter(PayoutRequest.partner_id == partner.id)
        .order_by(PayoutRequest.created_at.desc())
        .all()
    )
    return payout_history


@router.post("/payout-request", response_model=PartnerPayoutRequestResponse)
@limiter.limit("10/minute")
def request_payout(
    request: Request,
    body: PayoutRequestBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partner requests to withdraw available earnings."""
    partner = _get_active_partner(db, current_user.id)

    amount = body.amount_naira
    if amount < MIN_PAYOUT:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum payout is ₦{MIN_PAYOUT:,}",
        )

    balance = calculate_partner_balance(db, partner.id)
    available_balance = balance["available"]

    if amount > available_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ₦{available_balance:,}",
        )

    payout = PayoutRequest(
        partner_id=partner.id,
        amount_naira=amount,
        status="PENDING",
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)

    return payout