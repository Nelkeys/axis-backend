from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Admin: creating quiz content ---

class QuestionCreateRequest(BaseModel):
    order: int = Field(..., ge=1)
    text: str = Field(..., min_length=5)
    options: List[str] = Field(..., min_length=2, max_length=6)
    correct_index: int = Field(..., ge=0)

class QuizCreateRequest(BaseModel):
    time_limit_minutes: int = Field(default=30, ge=5, le=120)

class QuestionAdminResponse(BaseModel):
    id: int
    order: int
    text: str
    options: List[str]
    correct_index: int   # fine here — admin-only route

    class Config:
        from_attributes = True

class QuizAdminDetailResponse(BaseModel):
    id: int
    course_id: int
    time_limit_minutes: int
    questions: List[QuestionAdminResponse]

    class Config:
        from_attributes = True


# --- Student: taking the quiz — NOTE no correct_index anywhere below ---

class QuestionForStudent(BaseModel):
    id: int
    order: int
    text: str
    options: List[str]

    class Config:
        from_attributes = True

class QuizStartResponse(BaseModel):
    attempt_id: int
    time_limit_minutes: int
    questions: List[QuestionForStudent]

class AnswerSubmission(BaseModel):
    question_id: int
    selected_index: int = Field(..., ge=0)

class QuizSubmitRequest(BaseModel):
    answers: List[AnswerSubmission]

class QuizSubmitResponse(BaseModel):
    score: int
    passed: bool
    status: str
    certificate_verification_code: Optional[str] = None