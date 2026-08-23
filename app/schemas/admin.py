from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class CourseUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    price: Optional[Decimal] = Field(None, gt=0)
    renewal_price: Optional[Decimal] = Field(None, gt=0)
    pass_percentage: Optional[int] = Field(None, ge=1, le=100)
    curriculum_tags: Optional[List[str]] = None


class QuestionUpdateRequest(BaseModel):
    order: Optional[int] = Field(None, ge=1)
    text: Optional[str] = Field(None, min_length=5)
    options: Optional[List[str]] = Field(None, min_length=2, max_length=6)
    correct_index: Optional[int] = Field(None, ge=0)


class QuizUpdateRequest(BaseModel):
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=120)


class EnrollmentAdminResponse(BaseModel):
    id: int
    user_id: int
    student_email: str
    student_name: Optional[str] = None
    course_id: int
    course_title: str
    status: str
    renewal_count: int
    access_expires_at: datetime

    class Config:
        from_attributes = True