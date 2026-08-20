from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course, CourseVersion
from app.models.content import Topic, Section
from app.models.admin import AdminUser
from app.core.dependencies import get_current_admin
from app.schemas.content import (
    TopicCreateRequest, TopicResponse,
    SectionCreateRequest, SectionResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin Content"])


@router.post("/courses/{course_id}/topics", response_model=TopicResponse)
def create_topic(
    course_id: int,
    data: TopicCreateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    # Topics attach to the current (latest) CourseVersion — the one
    # created automatically when the course was made, or the newest
    # one if the course has since been re-versioned.
    version = (
        db.query(CourseVersion)
        .filter(CourseVersion.course_id == course_id)
        .order_by(CourseVersion.version_number.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status_code=500, detail="Course has no version — data integrity issue")

    topic = Topic(course_version_id=version.id, order=data.order, title=data.title)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.post("/topics/{topic_id}/sections", response_model=SectionResponse)
def create_section(
    topic_id: int,
    data: SectionCreateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    section = Section(
        topic_id=topic_id,
        order=data.order,
        title=data.title,
        text_content=data.text_content,
        video_url=data.video_url,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.get("/courses/{course_id}/full", response_model=list[TopicResponse])
def get_course_topics(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    # Quick way to confirm what's been built so far for a course.
    version = (
        db.query(CourseVersion)
        .filter(CourseVersion.course_id == course_id)
        .order_by(CourseVersion.version_number.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Course not found")

    return db.query(Topic).filter(Topic.course_version_id == version.id).order_by(Topic.order).all()