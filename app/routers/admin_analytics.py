from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.referral import Partner, PartnerEarning
from app.schemas.analytics import AdminAnalyticsResponse

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get("", response_model=AdminAnalyticsResponse)
def get_admin_analytics(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    High-level dashboard metrics. 
    Uses SQL-level aggregations for speed, even with thousands of users.
    """

    # ── 1. STUDENT & VIRAL METRICS ─────────────────────────
    total_students = db.query(User).count()
    
    referred_students = (
        db.query(User)
        .filter(User.referred_by.isnot(None))
        .count()
    )
    
    referral_share = (referred_students / total_students * 100) if total_students > 0 else 0.0

    # ── 2. ENGAGEMENT & PRODUCT METRICS ────────────────────
    total_enrollments = db.query(Enrollment).count()
    
    completed_enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.status == EnrollmentStatus.COMPLETED.value)
        .count()
    )
    
    completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0.0

    # Attach Rate: Students who have purchased more than 1 course
    multi_course_subquery = (
        db.query(Enrollment.user_id)
        .group_by(Enrollment.user_id)
        .having(func.count(Enrollment.id) > 1)
        .subquery()
    )
    multi_course_students = db.query(func.count()).select_from(multi_course_subquery).scalar() or 0
    
    attach_rate = (multi_course_students / total_students * 100) if total_students > 0 else 0.0

    # ── 3. DISTRIBUTION & UNIT ECONOMICS ───────────────────
    active_partners = (
        db.query(Partner)
        .filter(Partner.status == "ACTIVE")
        .count()
    )

    # Total cash committed to partners (earned + pending + paid)
    total_commissions = (
        db.query(func.coalesce(func.sum(PartnerEarning.amount_naira), 0))
        .scalar()
    )

    # Students specifically brought in by ACTIVE partners (not normal users)
    partner_user_ids_subquery = (
        db.query(Partner.user_id)
        .filter(Partner.status == "ACTIVE")
        .subquery()
    )
    users_by_partners = (
        db.query(User)
        .filter(User.referred_by.in_(partner_user_ids_subquery))
        .count()
    )

    # Partner CAC = Total Commissions / Users Acquired by Partners
    partner_cac = (total_commissions / users_by_partners) if users_by_partners > 0 else 0.0

    return AdminAnalyticsResponse(
        total_students=total_students,
        referred_students=referred_students,
        referral_share_percent=round(referral_share, 2),
        
        total_enrollments=total_enrollments,
        completed_enrollments=completed_enrollments,
        completion_rate_percent=round(completion_rate, 2),
        
        multi_course_students=multi_course_students,
        attach_rate_percent=round(attach_rate, 2),
        
        active_partners=active_partners,
        total_partner_commissions_naira=int(total_commissions),
        users_acquired_by_partners=users_by_partners,
        partner_cac_naira=round(float(partner_cac), 2),
    )