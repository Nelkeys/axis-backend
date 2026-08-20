from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.database import Base

class PaystackEventLog(Base):
    __tablename__ = "paystack_event_logs"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True) # Paystack's unique ID for this event
    event_type = Column(String, nullable=False)
    reference = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())