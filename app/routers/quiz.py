# app/routers/quiz.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, Question
from app.core.dependencies import get_current_user
from app.schemas.quiz import (
    QuizStartResponse, 
    QuestionForStudent, 
    QuizSubmitRequest, 
    QuizSubmitResponse
)
from app.services import quiz_service

router = APIRouter(prefix="/enrollments", tags=["Quiz"])


def _get_owned_enrollment(db: Session, enrollment_id: int, user: User) -> Enrollment:
    """Security boundary: ensures the student only accesses their own enrollment."""
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id, Enrollment.user_id == user.id)
        .first()
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found or access denied")
    return enrollment


@router.post("/{enrollment_id}/quiz/start", response_model=QuizStartResponse)
def start_quiz(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)
    attempt = quiz_service.start_quiz(db, enrollment)

    questions = (
        db.query(Question)
        .filter(Question.quiz_id == attempt.quiz_id)
        .order_by(Question.order)
        .all()
    )
    
    # Fetch the quiz object to get the time limit
    quiz_obj = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()

    return QuizStartResponse(
        attempt_id=attempt.id,
        time_limit_minutes=quiz_obj.time_limit_minutes,
        questions=[QuestionForStudent.model_validate(q) for q in questions],
    )


@router.post("/{enrollment_id}/quiz/{attempt_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    enrollment_id: int,
    attempt_id: int,
    data: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = _get_owned_enrollment(db, enrollment_id, current_user)
    result = quiz_service.submit_quiz(db, enrollment, attempt_id, data.answers)
    return QuizSubmitResponse(**result)