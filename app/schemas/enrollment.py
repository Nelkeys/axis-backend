from pydantic import BaseModel
from datetime import datetime
from typing import List

class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    course_version_id: int
    status: str
    first_purchased_at: datetime
    access_expires_at: datetime
    renewal_count: int

    class Config:
        from_attributes = True

class ProgressMarkRequest(BaseModel):
    section_id: int

class ProgressResponse(BaseModel):
    section_id: int
    completed_at: datetime

    class Config:
        from_attributes = True