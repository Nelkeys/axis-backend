from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.config import settings
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.course import Course
from app.models.notification import Notification, NotificationType
from app.services.enrollment_service import expire_stale_enrollments
from app.services.notification_service import notify_access_expiring

router = APIRouter(prefix="/cron", tags=["Cron"])

REMINDER_DAYS = [7, 3, 1]


def send_expiry_reminders(db: Session) -> int:
    """
    Sends reminders for enrollments expiring in 7, 3, or 1 day.
    Prevents duplicate reminders by checking if one was already sent today.
    """
    now = datetime.now(timezone.utc)
    reminders_sent = 0

    for days in REMINDER_DAYS:
        # Find enrollments expiring within this window
        window_start = now + timedelta(days=days - 1)
        window_end = now + timedelta(days=days)

        expiring = (
            db.query(Enrollment)
            .filter(
                Enrollment.status == EnrollmentStatus.ACTIVE.value,
                Enrollment.access_expires_at >= window_start,
                Enrollment.access_expires_at < window_end,
            )
            .all()
        )

        for enrollment in expiring:
            # Check if we already sent this specific reminder today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            already_sent = (
                db.query(Notification)
                .filter(
                    Notification.user_id == enrollment.user_id,
                    Notification.type == NotificationType.ACCESS_EXPIRING_SOON.value,
                    Notification.created_at >= today_start,
                )
                .first()
            )
            if already_sent:
                continue

            course = db.query(Course).filter(Course.id == enrollment.course_id).first()
            notify_access_expiring(db, enrollment.user_id, course.title, days)
            reminders_sent += 1

    return reminders_sent


@router.get("/run")
def run_cron_tasks(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Called by cron-job.org every 10-15 minutes.
    1. Keeps Render server alive.
    2. Locks expired enrollments.
    3. Sends expiry reminders (7, 3, 1 day before).
    """
    cron_secret = request.headers.get("x-cron-secret")
    if not cron_secret or cron_secret != settings.cron_secret_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    locked_count = expire_stale_enrollments(db)
    reminders_sent = send_expiry_reminders(db)

    return {
        "status": "ok",
        "enrollments_locked": locked_count,
        "reminders_sent": reminders_sent,
    }