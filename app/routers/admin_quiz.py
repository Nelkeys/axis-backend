from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.quiz import Quiz, Question
from app.models.admin import AdminUser
from app.core.dependencies import get_current_admin
from app.schemas.quiz import QuizCreateRequest, QuestionCreateRequest, QuestionAdminResponse

router = APIRouter(prefix="/admin", tags=["Admin Quiz"])


@router.post("/courses/{course_id}/quiz")
def create_quiz(
    course_id: int,
    data: QuizCreateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = db.query(Quiz).filter(Quiz.course_id == course_id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="This course already has a quiz")

    quiz = Quiz(course_id=course_id, time_limit_minutes=data.time_limit_minutes)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return {"quiz_id": quiz.id, "time_limit_minutes": quiz.time_limit_minutes}


@router.post("/quizzes/{quiz_id}/questions", response_model=QuestionAdminResponse)
def add_question(
    quiz_id: int,
    data: QuestionCreateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if data.correct_index >= len(data.options):
        raise HTTPException(status_code=400, detail="correct_index is out of range for the given options")

    question = Question(
        quiz_id=quiz_id,
        order=data.order,
        text=data.text,
        options=data.options,
        correct_index=data.correct_index,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question