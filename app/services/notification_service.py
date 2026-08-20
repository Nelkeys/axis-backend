# app/services/notification_service.py
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType


def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
) -> Notification:
    """Creates a single in-app notification."""
    notification = Notification(
        user_id=user_id,
        type=notification_type.value,
        title=title,
        message=message,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def notify_enrollment_confirmed(db: Session, user_id: int, course_title: str):
    create_notification(
        db, user_id,
        NotificationType.ENROLLMENT_CONFIRMED,
        title="Enrollment Confirmed",
        message=f"You have been successfully enrolled in '{course_title}'. You have 90 days of access. Start learning now!",
    )


def notify_quiz_passed(db: Session, user_id: int, course_title: str, score: int):
    create_notification(
        db, user_id,
        NotificationType.QUIZ_PASSED,
        title="Quiz Passed",
        message=f"Congratulations! You scored {score}% on the '{course_title}' quiz.",
    )


def notify_quiz_failed(db: Session, user_id: int, course_title: str, score: int, pass_percentage: int):
    create_notification(
        db, user_id,
        NotificationType.QUIZ_FAILED,
        title="Quiz Not Passed",
        message=f"You scored {score}% on the '{course_title}' quiz. You need {pass_percentage}% to pass. You can retake the quiz anytime.",
    )


def notify_certificate_issued(db: Session, user_id: int, course_title: str, verification_code: str):
    create_notification(
        db, user_id,
        NotificationType.CERTIFICATE_ISSUED,
        title="Certificate Issued",
        message=f"Your certificate for '{course_title}' is ready. Verification code: {verification_code}",
    )


def notify_access_expiring(db: Session, user_id: int, course_title: str, days_left: int):
    create_notification(
        db, user_id,
        NotificationType.ACCESS_EXPIRING_SOON,
        title=f"Access Expiring in {days_left} Day{'s' if days_left > 1 else ''}",
        message=f"Your access to '{course_title}' expires in {days_left} day{'s' if days_left > 1 else ''}. Complete your coursework or prepare to renew.",
    )


def notify_access_locked(db: Session, user_id: int, course_title: str, can_renew: bool):
    if can_renew:
        action = "You can renew at a discounted price."
    else:
        action = "A full repurchase is required to regain access."

    create_notification(
        db, user_id,
        NotificationType.ACCESS_LOCKED,
        title="Course Access Locked",
        message=f"Your access to '{course_title}' has expired and been locked. {action}",
    )