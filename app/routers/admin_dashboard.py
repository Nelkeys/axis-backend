# app/routers/admin_dashboard.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.admin import AdminUser
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User
from app.core.dependencies import get_current_admin
from app.schemas.admin import EnrollmentAdminResponse

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get("/enrollments", response_model=List[EnrollmentAdminResponse])
def list_all_enrollments(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin view of all enrollments across all students."""
    return db.query(Enrollment).order_by(Enrollment.id.desc()).all()


@router.get("/students", response_model=list)
def list_all_students(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin view of all registered students."""
    students = db.query(User).all()
    return [
        {"id": s.id, "email": s.email, "name": getattr(s, "name", None)}
        for s in students
    ]


@router.patch("/enrollments/{enrollment_id}/unlock")
def admin_unlock_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Customer support override: manually unlock an enrollment.
    Use when Paystack payment succeeded but webhook failed.
    Extends access by 90 days from now.
    """
    from datetime import datetime, timedelta, timezone

    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.status = EnrollmentStatus.ACTIVE.value
    enrollment.access_expires_at = datetime.now(timezone.utc) + timedelta(days=90)

    db.commit()
    db.refresh(enrollment)
    return {
        "status": "unlocked",
        "enrollment_id": enrollment.id,
        "new_expiry": str(enrollment.access_expires_at),
    }