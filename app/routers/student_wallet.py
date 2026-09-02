from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.enrollment import Enrollment
from app.models.referral import Partner, CoinEntry, PartnerEarning
from app.core.dependencies import get_current_user
from app.services.referral_service import get_coin_balance, calculate_partner_balance
from app.schemas.wallet import WalletSummaryResponse, CoinHistoryResponse, InviteeResponse

router = APIRouter(prefix="/wallet", tags=["Student Wallet"])


@router.get("/summary", response_model=WalletSummaryResponse)
def get_wallet_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invitee_count = db.query(User).filter(User.referred_by == current_user.id).count()

    partner = db.query(Partner).filter(
        Partner.user_id == current_user.id,
        Partner.status == "ACTIVE",
    ).first()

    is_partner = bool(partner)
    coin_balance = 0
    partner_available_cash = 0
    partner_pending_cash = 0

    if is_partner:
        balance = calculate_partner_balance(db, partner.id)
        partner_available_cash = balance["available"]
        partner_pending_cash = balance["pending_hold"]
    else:
        coin_balance = get_coin_balance(db, current_user.id)

    return WalletSummaryResponse(
        referral_code=current_user.referral_code,
        invitee_count=invitee_count,
        is_partner=is_partner,
        coin_balance=coin_balance,
        partner_available_cash=partner_available_cash,
        partner_pending_cash=partner_pending_cash,
    )


@router.get("/coin-history", response_model=CoinHistoryResponse)
def get_coin_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the student's coin ledger (earned + spent), newest first."""
    entries = (
        db.query(CoinEntry)
        .filter(CoinEntry.user_id == current_user.id)
        .order_by(CoinEntry.created_at.desc())
        .all()
    )
    balance = get_coin_balance(db, current_user.id)

    return CoinHistoryResponse(
        balance=balance,
        entries=entries,
    )



@router.get("/invitees", response_model=List[InviteeResponse])
def get_my_invitees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all users invited by the current user."""
    # 1. Fetch all users who have this user as their referrer
    invitees = (
        db.query(User)
        .filter(User.referred_by == current_user.id)
        .order_by(User.created_at.desc())  # Assuming User model has created_at; if not, remove .order_by
        .all()
    )

    result = []
    for invitee in invitees:
        # Check if they have at least one active or locked enrollment (meaning they paid)
        has_paid = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == invitee.id)
            .first() is not None
        )

        earned = 0
        # If the current user is a partner, calculate specific earnings from this invitee
        partner = db.query(Partner).filter(
            Partner.user_id == current_user.id,
            Partner.status == "ACTIVE"
        ).first()
        if partner:
            earned = (
                db.query(func.coalesce(func.sum(PartnerEarning.amount_naira), 0))
                .filter(
                    PartnerEarning.partner_id == partner.id,
                    PartnerEarning.source_user_id == invitee.id,
                )
                .scalar()
            )
            earned = int(earned)

        # Determine join date (use created_at if available on User, else dummy)
        joined_at = getattr(invitee, "created_at", None)
        if joined_at is None:
            joined_at = datetime.now(timezone.utc) # Fallback if column missing

        result.append(InviteeResponse(
            id=invitee.id,
            email=invitee.email,
            joined_at=joined_at,
            has_paid=has_paid,
            earned_from_them=earned,
        ))

    return result