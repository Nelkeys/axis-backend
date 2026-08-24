from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    course_version_id: int  # ADD THIS
    status: str
    renewal_count: int
    access_expires_at: Optional[datetime]
    first_purchased_at: Optional[datetime]  
    course_title: str
    price: Decimal
    renewal_price: Decimal
    progress_percent: int
    renewal_available: bool

    class Config:
        from_attributes = True

class ProgressMarkRequest(BaseModel):
    section_id: int

class ProgressResponse(BaseModel):
    section_id: int
    completed_at: datetime

    class Config:
        from_attributes = True