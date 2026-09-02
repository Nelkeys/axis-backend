from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    workos_user_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    referral_code = Column(String, unique=True, nullable=True)
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())