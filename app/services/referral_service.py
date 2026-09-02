from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.referral import Partner, CoinEntry, PartnerEarning, PayoutRequest

COIN_RATE = 0.03        # 3% back in coins for user referrers
PARTNER_RATE = 0.05     # 5% back in cash for partner referrers
HOLD_DAYS = 7           # partner earnings unlock after 7 days


def get_coin_balance(db: Session, user_id: int) -> int:
    """Return the user's coin balance (sum of ledger). 1 coin = 1 naira."""
    total = (
        db.query(func.coalesce(func.sum(CoinEntry.amount), 0))
        .filter(CoinEntry.user_id == user_id)
        .scalar()
    )
    return int(total)


def calculate_partner_balance(db: Session, partner_id: int) -> dict:
    """
    Single source of truth for a partner's balance.
    Used by both /wallet/summary and /partner/payout-request so they never drift.
    """
    now = datetime.now(timezone.utc)

    total_earned = (
        db.query(func.coalesce(func.sum(PartnerEarning.amount_naira), 0))
        .filter(
            PartnerEarning.partner_id == partner_id,
            PartnerEarning.available_at <= now,
        )
        .scalar()
    )
    total_pending_hold = (
        db.query(func.coalesce(func.sum(PartnerEarning.amount_naira), 0))
        .filter(
            PartnerEarning.partner_id == partner_id,
            PartnerEarning.available_at > now,
        )
        .scalar()
    )
    already_paid = (
        db.query(func.coalesce(func.sum(PayoutRequest.amount_naira), 0))
        .filter(
            PayoutRequest.partner_id == partner_id,
            PayoutRequest.status == "PAID",
        )
        .scalar()
    )
    pending_requests = (
        db.query(func.coalesce(func.sum(PayoutRequest.amount_naira), 0))
        .filter(
            PayoutRequest.partner_id == partner_id,
            PayoutRequest.status == "PENDING",
        )
        .scalar()
    )

    return {
        "available": int(total_earned) - int(already_paid) - int(pending_requests),
        "pending_hold": int(total_pending_hold),
    }


def grant_referral_reward(
    db: Session,
    payer: User,
    amount_paid_naira: float,
    reference: str,
):
    """
    Called from the Paystack webhook on every successful charge.
    Pays the payer's referrer continuously:
    - 3% in coins if referrer is a normal user
    - 5% in cash if referrer is an active partner
    """
    if not payer.referred_by:
        return

    referrer = db.query(User).filter(User.id == payer.referred_by).first()
    if referrer is None or referrer.id == payer.id:
        return

    partner = db.query(Partner).filter(
        Partner.user_id == referrer.id,
        Partner.status == "ACTIVE",
    ).first()

    if partner:
        earning = PartnerEarning(
            partner_id=partner.id,
            source_user_id=payer.id,
            payment_reference=reference,
            amount_naira=int(round(amount_paid_naira * PARTNER_RATE)),
            available_at=datetime.now(timezone.utc) + timedelta(days=HOLD_DAYS),
        )
        db.add(earning)
    else:
        coins = int(round(amount_paid_naira * COIN_RATE))
        if coins > 0:
            db.add(CoinEntry(
                user_id=referrer.id,
                amount=coins,
                type="REFERRAL_REWARD",
                reference=reference,
            ))