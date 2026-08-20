from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz_attempt import Certificate
from app.models.enrollment import Enrollment
from app.models.user import User
from app.models.course import Course
from app.schemas.certificate import CertificateVerifyResponse

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("/verify/{verification_code}", response_model=CertificateVerifyResponse)
def verify_certificate(
    verification_code: str,
    db: Session = Depends(get_db),
):
    """
    Public endpoint. Employers or anyone can verify a certificate
    by its unique code. No authentication required.
    """

    certificate = (
        db.query(Certificate)
        .filter(Certificate.verification_code == verification_code)
        .first()
    )
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == certificate.enrollment_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    user = db.query(User).filter(User.id == enrollment.user_id).first()
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()

    # Use 'name' if your User model has it, otherwise fall back to email
    student_name = getattr(user, "name", None) or user.email

    return CertificateVerifyResponse(
        student_name=student_name,
        course_title=course.title,
        score=certificate.score,
        verification_code=certificate.verification_code,
        issued_at=certificate.issued_at,
    )