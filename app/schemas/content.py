from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TopicCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    order: int = Field(..., ge=1)

class TopicResponse(BaseModel):
    id: int
    course_version_id: int
    order: int
    title: str

    class Config:
        from_attributes = True


class SectionCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    order: int = Field(..., ge=1)
    text_content: str = Field(..., min_length=10)
    video_url: Optional[str] = None

class SectionResponse(BaseModel):
    id: int
    topic_id: int
    order: int
    title: str
    text_content: str
    video_url: Optional[str]

    class Config:
        from_attributes = True


class SectionContentResponse(BaseModel):
    """Full content — only returned to enrolled, active students."""
    id: int
    title: str
    text_content: str
    video_url: Optional[str] = None

    class Config:
        from_attributes = True


class ProgressOverview(BaseModel):
    total_sections: int
    completed_sections: int
    percentage_complete: int


class QuizAttemptHistoryItem(BaseModel):
    attempt_id: int
    status: str
    score: Optional[int] = None
    started_at: datetime
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudentCertificateResponse(BaseModel):
    course_title: str
    score: int
    verification_code: str
    issued_at: datetime