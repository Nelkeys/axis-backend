from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

class CourseCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    price: Decimal = Field(..., gt=0)
    renewal_price: Decimal = Field(..., gt=0)
    pass_percentage: int = Field(default=70, ge=1, le=100)
    curriculum_tags: List[str] = Field(default_factory=list)

class CourseResponse(BaseModel):
    id: int
    title: str
    description: str
    price: Decimal
    renewal_price: Decimal
    pass_percentage: int
    curriculum_tags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SectionPreview(BaseModel):
    id: int
    title: str
    order: int

    class Config:
        from_attributes = True


class TopicPreview(BaseModel):
    id: int
    title: str
    order: int
    sections: List[SectionPreview] = []

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    """What students see when browsing the course catalog."""
    id: int
    title: str
    description: str
    price: Decimal
    renewal_price: Decimal
    pass_percentage: int
    curriculum_tags: List[str]

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseListResponse):
    """Full course view — includes structure and enrollment status."""
    topics: List[TopicPreview] = []
    is_enrolled: bool = False
    enrollment_status: Optional[str] = None

    class Config:
        from_attributes = True