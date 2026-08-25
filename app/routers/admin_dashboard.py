from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session, joinedload
from app.core.audit import log_audit
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.admin import AdminUser
from app.models.enrollment import Enrollment, EnrollmentStatus, Progress
from app.models.user import User
from app.models.course import Course
from app.models.audit import AuditLog
from app.core.dependencies import get_current_admin
from app.schemas.admin import EnrollmentAdminResponse, AuditLogResponse

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


@router.get("/students")
def list_all_students(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    students = db.query(User).all()

    result = []
    for s in students:
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == s.id).all()
        enrollment_count = len(enrollments)
        has_active = any(e.status == EnrollmentStatus.ACTIVE.value for e in enrollments)

        if enrollment_count == 0:
            status = "new"
        elif has_active:
            status = "enrolled"
        else:
            status = "inactive"

        result.append({
            "id": s.id,
            "email": s.email,
            "name": getattr(s, "name", None),
            "created_at": s.created_at,
            "enrollment_count": enrollment_count,
            "status": status,
        })

    return result


@router.patch("/enrollments/{enrollment_id}/unlock")
def admin_unlock_enrollment(
    enrollment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Customer support override: manually unlock an enrollment.
    Use when Paystack payment succeeded but webhook failed.
    Extends access by 90 days from now.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.status = EnrollmentStatus.ACTIVE.value
    enrollment.access_expires_at = datetime.now(timezone.utc) + timedelta(days=90)

    user = db.query(User).filter(User.id == enrollment.user_id).first()
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()

    log_audit(
        db=db,
        admin=current_admin,
        action="MANUAL_UNLOCK",
        entity_type="Enrollment",
        entity_id=enrollment_id,
        ip_address=request.client.host if request.client else "unknown",
        details={
            "student_email": user.email if user else f"User #{enrollment.user_id}",
            "course_title": course.title if course else f"Course #{enrollment.course_id}",
        },
    )

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
    request: Request,
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

    user = db.query(User).filter(User.id == enrollment.user_id).first()
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()

    log_audit(
        db=db,
        admin=current_admin,
        action="FORCE_LOCK",
        entity_type="Enrollment",
        entity_id=enrollment_id,
        ip_address=request.client.host if request.client else "unknown",
        details={
            "student_email": user.email if user else f"User #{enrollment.user_id}",
            "course_title": course.title if course else f"Course #{enrollment.course_id}",
        },
    )

    db.commit()
    return {"status": "locked", "enrollment_id": enrollment.id}


@router.delete("/enrollments/{enrollment_id}/progress")
def admin_reset_progress(
    enrollment_id: int,
    request: Request,
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

    user = db.query(User).filter(User.id == enrollment.user_id).first()
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()

    log_audit(
        db=db,
        admin=current_admin,
        action="RESET_PROGRESS",
        entity_type="Enrollment",
        entity_id=enrollment_id,
        ip_address=request.client.host if request.client else "unknown",
        details={
            "student_email": user.email if user else f"User #{enrollment.user_id}",
            "course_title": course.title if course else f"Course #{enrollment.course_id}",
            "sections_cleared": deleted_count,
        },
    )

    db.commit()
    return {"status": "reset", "sections_cleared": deleted_count}


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    admin_email: Optional[str] = Query(default=None),
):
    """
    Retrieve audit logs with optional filtering.
    Returns newest first, paginated.
    """
    query = db.query(AuditLog).options(joinedload(AuditLog.admin))

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if admin_email:
        query = query.join(AdminUser).filter(AdminUser.email.ilike(f"%{admin_email}%"))

    logs = (
        query
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        AuditLogResponse(
            id=log.id,
            admin_email=log.admin.email if log.admin else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]