from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.enrollment import Enrollment
from app.core.dependencies import get_current_user
from app.schemas.enrollment import EnrollmentResponse, ProgressMarkRequest, ProgressResponse
from app.services import enrollment_service

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


def _get_owned_enrollment(db: Session, enrollment_id: int, user: User) -> Enrollment:
    # This is the ownership check that closes the IDOR loophole discussed earlier —
    # every route below MUST filter by user_id, never trust the URL alone.
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id, Enrollment.user_id == user.id)
        .first()
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


@router.get("", response_model=list[EnrollmentResponse])
def list_my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_enrollment(db, enrollment_id, current_user)


@router.post("/{enrollment_id}/progress", response_model=ProgressResponse)
def mark_progress(
    enrollment_id: int,
    data: ProgressMarkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)
    return enrollment_service.mark_section_complete(db, enrollment, data.section_id)