from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    COMPLETED = "COMPLETED"

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course_version_id = Column(Integer, ForeignKey("course_versions.id"), nullable=False)
    status = Column(String, nullable=False, default=EnrollmentStatus.ACTIVE.value)
    first_purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    access_expires_at = Column(DateTime(timezone=True), nullable=False)
    renewal_count = Column(Integer, nullable=False, default=0)

    progress = relationship("Progress", back_populates="enrollment")


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollment = relationship("Enrollment", back_populates="progress")