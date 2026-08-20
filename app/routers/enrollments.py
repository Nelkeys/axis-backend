# app/routers/enrollments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.enrollment import Enrollment, EnrollmentStatus, Progress
from app.models.content import Topic, Section
from app.models.course import Course
from app.models.quiz_attempt import QuizAttempt, Certificate
from app.core.dependencies import get_current_user
from app.schemas.enrollment import EnrollmentResponse, ProgressMarkRequest, ProgressResponse
from app.schemas.content import (
    SectionContentResponse,
    ProgressOverview,
    QuizAttemptHistoryItem,
    StudentCertificateResponse,
)
from app.services import enrollment_service

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


def _get_owned_enrollment(db: Session, enrollment_id: int, user: User) -> Enrollment:
    """
    IDOR protection — every route below MUST filter by user_id,
    never trust the URL alone.
    """
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id, Enrollment.user_id == user.id)
        .first()
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


# ============================================================
# LIST (no path params — most specific)
# ============================================================

@router.get("", response_model=list[EnrollmentResponse])
def list_my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()


# ============================================================
# SECTION CONTENT (deepest path first)
# ============================================================

@router.get("/{enrollment_id}/sections/{section_id}", response_model=SectionContentResponse)
def get_section_content(
    enrollment_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full text_content and video_url.
    Only accessible if enrolled AND status is ACTIVE or COMPLETED.
    """
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)

    if enrollment.status not in (EnrollmentStatus.ACTIVE.value, EnrollmentStatus.COMPLETED.value):
        raise HTTPException(status_code=403, detail="Course is locked — renew to continue")

    # Verify the section belongs to this enrollment's course version
    section = (
        db.query(Section)
        .join(Topic, Section.topic_id == Topic.id)
        .filter(
            Section.id == section_id,
            Topic.course_version_id == enrollment.course_version_id,
        )
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found in this course")

    return section


# ============================================================
# PROGRESS OVERVIEW (GET)
# ============================================================

@router.get("/{enrollment_id}/progress", response_model=ProgressOverview)
def get_progress_overview(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Shows completed vs total sections for this enrollment."""
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)

    total_sections = (
        db.query(Section)
        .join(Topic, Section.topic_id == Topic.id)
        .filter(Topic.course_version_id == enrollment.course_version_id)
        .count()
    )

    completed_sections = (
        db.query(Progress)
        .filter(Progress.enrollment_id == enrollment.id)
        .count()
    )

    percentage = round((completed_sections / total_sections) * 100) if total_sections > 0 else 0

    return ProgressOverview(
        total_sections=total_sections,
        completed_sections=completed_sections,
        percentage_complete=percentage,
    )


# ============================================================
# MARK SECTION COMPLETE (POST)
# ============================================================

@router.post("/{enrollment_id}/progress", response_model=ProgressResponse)
def mark_progress(
    enrollment_id: int,
    data: ProgressMarkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)
    return enrollment_service.mark_section_complete(db, enrollment, data.section_id)


# ============================================================
# QUIZ ATTEMPT HISTORY
# ============================================================

@router.get("/{enrollment_id}/quiz/history", response_model=List[QuizAttemptHistoryItem])
def get_quiz_history(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All quiz attempts for this enrollment, newest first."""
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)

    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.enrollment_id == enrollment.id)
        .order_by(QuizAttempt.started_at.desc())
        .all()
    )
    return [
        QuizAttemptHistoryItem(
            attempt_id=a.id,
            status=a.status,
            score=a.score,
            started_at=a.started_at,
            submitted_at=a.submitted_at,
        )
        for a in attempts
    ]


# ============================================================
# STUDENT CERTIFICATE
# ============================================================

@router.get("/{enrollment_id}/certificate", response_model=StudentCertificateResponse)
def get_my_certificate(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the student's earned certificate for this enrollment."""
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)

    certificate = (
        db.query(Certificate)
        .filter(Certificate.enrollment_id == enrollment.id)
        .first()
    )
    if not certificate:
        raise HTTPException(status_code=404, detail="No certificate earned yet")

    course = db.query(Course).filter(Course.id == enrollment.course_id).first()

    return StudentCertificateResponse(
        course_title=course.title,
        score=certificate.score,
        verification_code=certificate.verification_code,
        issued_at=certificate.issued_at,
    )


# ============================================================
# SINGLE ENROLLMENT (generic catch-all — MUST be last)
# ============================================================

@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_enrollment(db, enrollment_id, current_user)