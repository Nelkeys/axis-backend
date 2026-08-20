from sqlalchemy import Column, Integer, String, Numeric, ARRAY, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)          # NGN, e.g. 3500.00
    renewal_price = Column(Numeric(10, 2), nullable=False)  # discounted re-lock price
    pass_percentage = Column(Integer, nullable=False, default=70)
    curriculum_tags = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    versions = relationship("CourseVersion", back_populates="course")


class CourseVersion(Base):
    __tablename__ = "course_versions"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="versions")
    topics = relationship("Topic", back_populates="course_version", order_by="Topic.order")