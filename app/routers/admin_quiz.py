from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.quiz import Quiz, Question
from app.models.admin import AdminUser
from app.core.dependencies import get_current_admin
from app.core.audit import log_audit
from app.schemas.quiz import QuizCreateRequest, QuestionCreateRequest, QuestionAdminResponse, QuizAdminDetailResponse
from app.schemas.admin import QuestionUpdateRequest, QuizUpdateRequest

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


@router.get("/quizzes/{quiz_id}", response_model=QuizAdminDetailResponse)
def get_quiz_detail(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.order)
        .all()
    )

    return QuizAdminDetailResponse(
        id=quiz.id,
        course_id=quiz.course_id,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=questions,
    )


@router.get("/courses/{course_id}/quiz", response_model=QuizAdminDetailResponse)
def get_quiz_by_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    quiz = db.query(Quiz).filter(Quiz.course_id == course_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="This course has no quiz yet")

    questions = (
        db.query(Question)
        .filter(Question.quiz_id == quiz.id)
        .order_by(Question.order)
        .all()
    )

    return QuizAdminDetailResponse(
        id=quiz.id,
        course_id=quiz.course_id,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=questions,
    )


@router.patch("/quizzes/{quiz_id}")
def update_quiz(
    quiz_id: int,
    data: QuizUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Update quiz time limit."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if data.time_limit_minutes is not None:
        quiz.time_limit_minutes = data.time_limit_minutes

    db.commit()
    db.refresh(quiz)
    return {"quiz_id": quiz.id, "time_limit_minutes": quiz.time_limit_minutes}


@router.patch("/questions/{question_id}", response_model=QuestionAdminResponse)
def update_question(
    question_id: int,
    data: QuestionUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Edit a question's text, options, or correct answer."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if data.text is not None:
        question.text = data.text
    if data.order is not None:
        question.order = data.order
    if data.options is not None:
        question.options = data.options
    if data.correct_index is not None:
        options = data.options if data.options is not None else question.options
        if data.correct_index >= len(options):
            raise HTTPException(status_code=400, detail="correct_index out of range")
        question.correct_index = data.correct_index

    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Remove a question from a quiz."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    log_audit(
        db=db,
        admin=current_admin,
        action="DELETE_QUESTION",
        entity_type="Question",
        entity_id=question_id,
        ip_address=request.client.host if request.client else "unknown",
        details={"text": question.text[:100]},
    )

    db.delete(question)
    db.commit()
    return {"status": "deleted", "question_id": question_id}