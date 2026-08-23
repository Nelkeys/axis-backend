from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.admin import AdminUser
from app.models.enrollment import Enrollment, EnrollmentStatus, Progress
from app.models.user import User
from app.models.course import Course
from app.core.dependencies import get_current_admin
from app.schemas.admin import EnrollmentAdminResponse

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get("/enrollments", response_model=List[EnrollmentAdminResponse])
def list_all_enrollments(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    enrollments = db.query(Enrollment).order_by(Enrollment.id.desc()).all()

    result = []
    for e in enrollments:
        user = db.query(User).filter(User.id == e.user_id).first()
        course = db.query(Course).filter(Course.id == e.course_id).first()
        result.append(
            EnrollmentAdminResponse(
                id=e.id,
                user_id=e.user_id,
                student_email=user.email if user else f"User #{e.user_id}",
                student_name=getattr(user, "name", None) if user else None,
                course_id=e.course_id,
                course_title=course.title if course else f"Course #{e.course_id}",
                status=e.status,
                renewal_count=e.renewal_count,
                access_expires_at=e.access_expires_at,
            )
        )
    return result


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


@router.patch("/enrollments/{enrollment_id}/force-lock")
def admin_force_lock_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Immediately locks an enrollment regardless of remaining access time.
    Use for refunds, fraud, or correcting an accidental unlock.
    Progress is preserved — this ends ACCESS, not the student's record.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.status = EnrollmentStatus.LOCKED.value
    db.commit()
    return {"status": "locked", "enrollment_id": enrollment.id}


@router.delete("/enrollments/{enrollment_id}/progress")
def admin_reset_progress(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Wipes all Progress rows for this enrollment so the student can restart
    the course from scratch. Does NOT affect status or access_expires_at.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    deleted_count = (
        db.query(Progress).filter(Progress.enrollment_id == enrollment_id).delete()
    )
    db.commit()
    return {"status": "reset", "sections_cleared": deleted_count}