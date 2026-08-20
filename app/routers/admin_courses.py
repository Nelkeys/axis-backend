from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course, CourseVersion
from app.models.admin import AdminUser
from app.core.dependencies import get_current_admin
from app.schemas.course import CourseCreateRequest, CourseResponse

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


@router.get("", response_model=list[CourseResponse])
def list_courses(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    return db.query(Course).all()