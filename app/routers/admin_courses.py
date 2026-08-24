from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course, CourseVersion
from app.models.enrollment import Enrollment
from app.models.admin import AdminUser
from app.core.dependencies import get_current_admin
from app.schemas.course import CourseCreateRequest, CourseResponse
from app.schemas.admin import CourseUpdateRequest

router = APIRouter(prefix="/admin/courses", tags=["Admin Courses"])

@router.post("", response_model=CourseResponse)
def create_course(
    data: CourseCreateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    course = Course(
        title=data.title,
        description=data.description,
        price=data.price,
        renewal_price=data.renewal_price,
        pass_percentage=data.pass_percentage,
        curriculum_tags=data.curriculum_tags,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # Every course starts with version 1 — this is what Topics/Sections attach to.
    initial_version = CourseVersion(course_id=course.id, version_number=1)
    db.add(initial_version)
    db.commit()

    return course


@router.patch("/{course_id}/publish")
def toggle_publish(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    course.is_published = not course.is_published
    db.commit()
    return {"id": course.id, "is_published": course.is_published}


@router.get("", response_model=list[CourseResponse])
def list_courses(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    return db.query(Course).all()



@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    data: CourseUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Edit course details. Only updates fields that are provided."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if data.title is not None:
        course.title = data.title
    if data.description is not None:
        course.description = data.description
    if data.price is not None:
        course.price = data.price
    if data.renewal_price is not None:
        course.renewal_price = data.renewal_price
    if data.pass_percentage is not None:
        course.pass_percentage = data.pass_percentage
    if data.curriculum_tags is not None:
        course.curriculum_tags = data.curriculum_tags

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Soft-delete: prevents new enrollments by setting price to 0.
    Hard-delete is dangerous because it would orphan enrollments,
    progress, payments, and certificates.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if anyone is enrolled
    enrollment_count = (
        db.query(Enrollment).filter(Enrollment.course_id == course_id).count()
    )
    if enrollment_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {enrollment_count} students are enrolled. Disable the course instead.",
        )

    db.delete(course)
    db.commit()
    return {"status": "deleted", "course_id": course_id}