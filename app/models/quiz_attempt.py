from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    status = Column(String, nullable=False, default=AttemptStatus.IN_PROGRESS.value)
    score = Column(Integer, nullable=True)          # percentage, set on submit
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False, unique=True)
    verification_code = Column(String, unique=True, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())