from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from app.database import Base
import enum


class NotificationType(str, enum.Enum):
    ENROLLMENT_CONFIRMED = "ENROLLMENT_CONFIRMED"
    QUIZ_PASSED = "QUIZ_PASSED"
    QUIZ_FAILED = "QUIZ_FAILED"
    CERTIFICATE_ISSUED = "CERTIFICATE_ISSUED"
    ACCESS_EXPIRING_SOON = "ACCESS_EXPIRING_SOON"
    ACCESS_LOCKED = "ACCESS_LOCKED"
    RENEWAL_REMINDER = "RENEWAL_REMINDER"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())