from pydantic import BaseModel, Field
from typing import Optional

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