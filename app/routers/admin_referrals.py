from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
import secrets

from app.database import get_db
from app.models.admin import AdminUser
from app.models.user import User
from app.models.referral import Partner, PartnerInvite
from app.core.dependencies import get_current_admin
from app.core.audit import log_audit
from app.schemas.referral import (
    PartnerInviteCreateRequest,
    PartnerInviteResponse,
    PartnerResponse,
    PayoutRequestResponse,
)
from app.services.email_service import send_partner_invite_email
from app.models.referral import PayoutRequest

router = APIRouter(prefix="/admin/referrals", tags=["Admin Referrals"])


def _generate_invite_code() -> str:
    return "RVP-" + secrets.token_hex(4).upper()


@router.post("/partner-invites", response_model=PartnerInviteResponse)
def create_partner_invite(
    data: PartnerInviteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    # GUARDRAIL 1: Must be an existing user
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="User not found."
        )

    # GUARDRAIL 2: Cannot invite an already active partner
    existing_partner = db.query(Partner).filter(
        Partner.user_id == user.id, 
        Partner.status == "ACTIVE"
    ).first()
    if existing_partner:
        raise HTTPException(
            status_code=400, 
            detail="This user is already an active partner."
        )

    # GUARDRAIL 3: Cannot have multiple unused invites for the same user
    existing_unused_invite = db.query(PartnerInvite).filter(
        PartnerInvite.email == data.email,
        PartnerInvite.used_by_user_id.is_(None)
    ).first()
    if existing_unused_invite:
        raise HTTPException(
            status_code=400, 
            detail="An active, unused invite already exists for this user."
        )

    # If they were previously revoked, block new invites and force reactivation instead
    revoked_partner = db.query(Partner).filter(
        Partner.user_id == user.id, 
        Partner.status == "REVOKED"
    ).first()
    if revoked_partner:
        raise HTTPException(
            status_code=400, 
            detail="This user is a revoked partner. Please use the 'Reactivate' action instead of sending a new invite."
        )

    # All checks passed, create the invite
    code = _generate_invite_code()
    invite = PartnerInvite(
        code=code,
        email=data.email,
        note=data.note,
        created_by_admin_id=current_admin.id,
    )
    db.add(invite)

    log_audit(
        db=db,
        admin=current_admin,
        action="PARTNER_INVITE_CREATED",
        entity_type="PartnerInvite",
        ip_address=request.client.host if request.client else "unknown",
        details={"code": code, "email": data.email, "note": data.note},
    )

    db.commit()
    db.refresh(invite)

    # Send the email. If it fails, still return the code so the admin can send it manually.
    email_sent = send_partner_invite_email(data.email, code)

    return PartnerInviteResponse(
        id=invite.id,
        code=invite.code,
        email=invite.email,
        note=invite.note,
        used_by_email=None,
        used_at=invite.used_at,
        created_at=invite.created_at,
        email_sent=email_sent,
    )


@router.get("/partner-invites", response_model=List[PartnerInviteResponse])
def list_partner_invites(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    # Only return invites that have an email (filter out old test data)
    invites = (
        db.query(PartnerInvite)
        .filter(PartnerInvite.email.isnot(None))
        .order_by(PartnerInvite.created_at.desc())
        .all()
    )
    result = []
    for inv in invites:
        used_by = (
            db.query(User).filter(User.id == inv.used_by_user_id).first()
            if inv.used_by_user_id else None
        )
        result.append(
            PartnerInviteResponse(
                id=inv.id,
                code=inv.code,
                email=inv.email,
                note=inv.note,
                used_by_email=used_by.email if used_by else None,
                used_at=inv.used_at,
                created_at=inv.created_at,
            )
        )
    return result


@router.get("/partners", response_model=List[PartnerResponse])
def list_partners(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    partners = db.query(Partner).order_by(Partner.created_at.desc()).all()
    result = []
    for p in partners:
        user = db.query(User).filter(User.id == p.user_id).first()
        invitee_count = (
            db.query(User).filter(User.referred_by == p.user_id).count()
        )
        result.append(
            PartnerResponse(
                id=p.id,
                user_email=user.email if user else f"User #{p.user_id}",
                referral_code=user.referral_code if user else None,
                status=p.status,
                invitee_count=invitee_count,
                total_earnings=0,  # filled in Part 2 when earnings exist
                created_at=p.created_at,
            )
        )
    return result


@router.patch("/partners/{partner_id}/revoke")
def revoke_partner(
    partner_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    partner.status = "REVOKED"

    user = db.query(User).filter(User.id == partner.user_id).first()

    log_audit(
        db=db,
        admin=current_admin,
        action="PARTNER_REVOKED",
        entity_type="Partner",
        entity_id=partner_id,
        ip_address=request.client.host if request.client else "unknown",
        details={"user_email": user.email if user else None},
    )

    db.commit()
    return {"status": "revoked", "partner_id": partner_id}


@router.patch("/partners/{partner_id}/reactivate")
def reactivate_partner(
    partner_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Reactivates a previously revoked partner."""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    if partner.status == "ACTIVE":
        raise HTTPException(status_code=400, detail="Partner is already active")

    partner.status = "ACTIVE"

    user = db.query(User).filter(User.id == partner.user_id).first()

    log_audit(
        db=db,
        admin=current_admin,
        action="PARTNER_REACTIVATED",
        entity_type="Partner",
        entity_id=partner_id,
        ip_address=request.client.host if request.client else "unknown",
        details={"user_email": user.email if user else None},
    )

    db.commit()
    return {"status": "reactivated", "partner_id": partner_id}


@router.get("/payouts", response_model=List[PayoutRequestResponse])
def list_payout_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    query = db.query(PayoutRequest)
    if status:
        query = query.filter(PayoutRequest.status == status)

    payouts = query.order_by(PayoutRequest.created_at.desc()).all()

    result = []
    for p in payouts:
        partner = db.query(Partner).filter(Partner.id == p.partner_id).first()
        user = db.query(User).filter(User.id == partner.user_id).first() if partner else None
        result.append(
            PayoutRequestResponse(
                id=p.id,
                partner_id=p.partner_id,
                partner_email=user.email if user else None,
                amount_naira=p.amount_naira,
                status=p.status,
                created_at=p.created_at,
                paid_at=p.paid_at,
            )
        )
    return result


@router.patch("/payouts/{payout_id}/approve")
def approve_payout(
    payout_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout request not found")

    if payout.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Payout is already {payout.status.lower()}")

    payout.status = "PAID"
    payout.paid_at = datetime.now(timezone.utc)

    partner = db.query(Partner).filter(Partner.id == payout.partner_id).first()
    user = db.query(User).filter(User.id == partner.user_id).first() if partner else None

    log_audit(
        db=db,
        admin=current_admin,
        action="PAYOUT_APPROVED",
        entity_type="PayoutRequest",
        entity_id=payout_id,
        ip_address=request.client.host if request.client else "unknown",
        details={
            "partner_email": user.email if user else None,
            "amount_naira": payout.amount_naira,
        },
    )

    db.commit()
    return {"status": "paid", "payout_id": payout_id, "amount": payout.amount_naira}


@router.patch("/payouts/{payout_id}/reject")
def reject_payout(
    payout_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout request not found")

    if payout.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Payout is already {payout.status.lower()}")

    payout.status = "REJECTED"

    partner = db.query(Partner).filter(Partner.id == payout.partner_id).first()
    user = db.query(User).filter(User.id == partner.user_id).first() if partner else None

    log_audit(
        db=db,
        admin=current_admin,
        action="PAYOUT_REJECTED",
        entity_type="PayoutRequest",
        entity_id=payout_id,
        ip_address=request.client.host if request.client else "unknown",
        details={
            "partner_email": user.email if user else None,
            "amount_naira": payout.amount_naira,
        },
    )

    db.commit()
    return {"status": "rejected", "payout_id": payout_id}