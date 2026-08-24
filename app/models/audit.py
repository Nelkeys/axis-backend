from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    
    action = Column(String, nullable=False)        # e.g., "FORCE_LOCK_ENROLLMENT"
    entity_type = Column(String, nullable=False)   # e.g., "Enrollment", "Course"
    entity_id = Column(Integer, nullable=True)     # ID of the affected record
    
    details = Column(JSON, nullable=True)          # Optional extra context
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to easily fetch admin details in the admin UI later
    admin = relationship("AdminUser")