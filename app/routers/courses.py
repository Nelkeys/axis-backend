# app/routers/courses.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.course import Course, CourseVersion
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.core.dependencies import get_current_user
from app.schemas.course import CourseListResponse, CourseDetailResponse

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=List[CourseListResponse])
def list_courses(
    search: str = None,
    tag: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Course).filter(Course.is_published == True)
    if search:
        query = query.filter(Course.title.ilike(f"%{search}%"))
    if tag:
        query = query.filter(Course.curriculum_tags.contains([tag]))
    return query.order_by(Course.created_at.desc()).all()


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course_detail(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Authenticated — shows structure + enrollment status."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found")

    version = (
        db.query(CourseVersion)
        .filter(CourseVersion.course_id == course_id)
        .order_by(CourseVersion.version_number.desc())
        .first()
    )

    topics = version.topics if version else []

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id, Enrollment.course_id == course_id)
        .first()
    )

    is_enrolled = enrollment is not None and enrollment.status in (
        EnrollmentStatus.ACTIVE.value,
        EnrollmentStatus.COMPLETED.value,
    )

    return CourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        price=course.price,
        renewal_price=course.renewal_price,
        pass_percentage=course.pass_percentage,
        curriculum_tags=course.curriculum_tags,
        topics=topics,
        is_enrolled=is_enrolled,
        enrollment_status=enrollment.status if enrollment else None,
    )