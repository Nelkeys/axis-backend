import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.quiz import Quiz, Question
from app.models.quiz_attempt import QuizAttempt, Certificate, AttemptStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.course import Course

from app.services.notification_service import (
    notify_quiz_passed,
    notify_quiz_failed,
    notify_certificate_issued,
)


def start_quiz(db: Session, enrollment: Enrollment) -> QuizAttempt:
    if enrollment.status not in (EnrollmentStatus.ACTIVE.value, EnrollmentStatus.COMPLETED.value):
        raise HTTPException(status_code=403, detail="Course is locked — renew to take the quiz")

    quiz = db.query(Quiz).filter(Quiz.course_id == enrollment.course_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="This course has no quiz configured yet")

    # One-sitting rule: any previous IN_PROGRESS attempt for this enrollment
    # is dead the moment a new one starts. No resuming, ever.
    stale_attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.enrollment_id == enrollment.id,
            QuizAttempt.status == AttemptStatus.IN_PROGRESS.value,
        )
        .all()
    )
    for stale in stale_attempts:
        stale.status = AttemptStatus.EXPIRED.value

    attempt = QuizAttempt(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id,
        status=AttemptStatus.IN_PROGRESS.value,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def submit_quiz(db: Session, enrollment: Enrollment, attempt_id: int, answers: list) -> dict:
    attempt = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.id == attempt_id, QuizAttempt.enrollment_id == enrollment.id)
        .first()
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    if attempt.status != AttemptStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=400, detail="This attempt is no longer active")

    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()

    # Hard one-sitting time limit — enforced server-side, not trusted from the client.
    deadline = attempt.started_at + timedelta(minutes=quiz.time_limit_minutes)
    if datetime.now(timezone.utc) > deadline:
        attempt.status = AttemptStatus.EXPIRED.value
        db.commit()
        raise HTTPException(status_code=400, detail="Time limit exceeded — attempt expired")

    if enrollment.status not in (EnrollmentStatus.ACTIVE.value, EnrollmentStatus.COMPLETED.value):
        # Enrollment could have locked mid-quiz — checked again at submit.
        attempt.status = AttemptStatus.EXPIRED.value
        db.commit()
        raise HTTPException(status_code=403, detail="Course locked during attempt — renew to retry")

    questions = {q.id: q for q in db.query(Question).filter(Question.quiz_id == quiz.id).all()}
    submitted = {a.question_id: a.selected_index for a in answers}

    correct_count = 0
    for qid, question in questions.items():
        if submitted.get(qid) == question.correct_index:
            correct_count += 1

    score = round((correct_count / len(questions)) * 100) if questions else 0

    course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    passed = score >= course.pass_percentage

    attempt.score = score
    attempt.status = AttemptStatus.PASSED.value if passed else AttemptStatus.FAILED.value
    attempt.submitted_at = datetime.now(timezone.utc)
    db.commit()

    certificate_code = None
    if passed:
        existing_cert = (
            db.query(Certificate).filter(Certificate.enrollment_id == enrollment.id).first()
        )
        if existing_cert is None:
            certificate_code = f"AXIS-{course.id}-{secrets.token_hex(4).upper()}"
            certificate = Certificate(
                enrollment_id=enrollment.id,
                verification_code=certificate_code,
                score=score,
            )
            db.add(certificate)
            enrollment.status = EnrollmentStatus.COMPLETED.value
            db.commit()

            # Notify: certificate issued
            notify_certificate_issued(db, enrollment.user_id, course.title, certificate_code)
        else:
            certificate_code = existing_cert.verification_code

        # Notify: quiz passed
        notify_quiz_passed(db, enrollment.user_id, course.title, score)
    else:
        # Notify: quiz failed
        notify_quiz_failed(db, enrollment.user_id, course.title, score, course.pass_percentage)

    return {
        "score": score,
        "passed": passed,
        "status": attempt.status,
        "certificate_verification_code": certificate_code,
    }