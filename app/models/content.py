from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    course_version_id = Column(Integer, ForeignKey("course_versions.id"), nullable=False)
    order = Column(Integer, nullable=False)
    title = Column(String, nullable=False)

    course_version = relationship("CourseVersion", back_populates="topics")
    sections = relationship("Section", back_populates="topic", order_by="Section.order")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    order = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    text_content = Column(Text, nullable=False)
    video_url = Column(String, nullable=True)  # optional, as decided

    topic = relationship("Topic", back_populates="sections")