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
    TopicUpdateRequest, SectionUpdateRequest,
    TopicWithSectionsResponse,
)
from app.models.enrollment import Progress


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


@router.get("/courses/{course_id}/full", response_model=list[TopicWithSectionsResponse])
def get_course_topics(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    version = (
        db.query(CourseVersion)
        .filter(CourseVersion.course_id == course_id)
        .order_by(CourseVersion.version_number.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Course not found")

    return db.query(Topic).filter(Topic.course_version_id == version.id).order_by(Topic.order).all()



@router.patch("/topics/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: int,
    data: TopicUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    if data.title is not None:
        topic.title = data.title
    if data.order is not None:
        topic.order = data.order

    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/topics/{topic_id}")
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Deleting a topic orphans its sections — check for that first.
    section_count = db.query(Section).filter(Section.topic_id == topic_id).count()
    if section_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: this topic has {section_count} section(s). Delete them first.",
        )

    db.delete(topic)
    db.commit()
    return {"status": "deleted", "topic_id": topic_id}


@router.patch("/sections/{section_id}", response_model=SectionResponse)
def update_section(
    section_id: int,
    data: SectionUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    if data.title is not None:
        section.title = data.title
    if data.order is not None:
        section.order = data.order
    if data.text_content is not None:
        section.text_content = data.text_content
    if data.video_url is not None:
        section.video_url = data.video_url

    db.commit()
    db.refresh(section)
    return section


@router.delete("/sections/{section_id}")
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    # Check if any student has already completed this section before deleting.
    # The DB foreign key would block this anyway, but we want a clean 400
    # instead of a raw 500 from a ForeignKeyViolation.
    progress_count = db.query(Progress).filter(Progress.section_id == section_id).count()
    if progress_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {progress_count} student(s) have completed this section. Edit it instead of deleting.",
        )

    db.delete(section)
    db.commit()
    return {"status": "deleted", "section_id": section_id}