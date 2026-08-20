from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.enrollment import Enrollment, Progress, EnrollmentStatus
from app.models.course import Course, CourseVersion

from app.services.notification_service import notify_enrollment_confirmed, notify_access_locked

ACCESS_WINDOW_DAYS = 90
MAX_RENEWALS_BEFORE_REPURCHASE = 1


def create_enrollment(db: Session, user_id: int, course_id: int) -> Enrollment:
    existing = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Already enrolled in this course")

    version = (
        db.query(CourseVersion)
        .filter(CourseVersion.course_id == course_id)
        .order_by(CourseVersion.version_number.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id,
        course_version_id=version.id,
        status=EnrollmentStatus.ACTIVE.value,
        access_expires_at=datetime.now(timezone.utc) + timedelta(days=ACCESS_WINDOW_DAYS),
        renewal_count=0,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)


    course = db.query(Course).filter(Course.id == course_id).first()
    notify_enrollment_confirmed(db, user_id, course.title)


    return enrollment


def renew_enrollment(db: Session, enrollment: Enrollment) -> Enrollment:
    if enrollment.status != EnrollmentStatus.LOCKED.value:
        raise HTTPException(status_code=400, detail="Only a locked enrollment can be renewed")

    if enrollment.renewal_count >= MAX_RENEWALS_BEFORE_REPURCHASE:
        # The one free renewal is already used — this must go through
        # repurchase_enrollment (full price) instead.
        raise HTTPException(
            status_code=400,
            detail="Renewal already used for this course. Full repurchase is required.",
        )

    enrollment.status = EnrollmentStatus.ACTIVE.value
    enrollment.access_expires_at = datetime.now(timezone.utc) + timedelta(days=ACCESS_WINDOW_DAYS)
    enrollment.renewal_count += 1
    db.commit()
    db.refresh(enrollment)
    return enrollment


def repurchase_enrollment(db: Session, enrollment: Enrollment) -> Enrollment:
    """
    Used once the one allowed renewal has already been consumed.
    Charged at full course price (enforced in the payment layer, piece 5) —
    this function only handles the state reset once payment is confirmed.
    Progress rows are untouched, matching the platform's core promise that
    finished sections are never lost.
    """
    if enrollment.status != EnrollmentStatus.LOCKED.value:
        raise HTTPException(status_code=400, detail="Only a locked enrollment can be repurchased")

    if enrollment.renewal_count < MAX_RENEWALS_BEFORE_REPURCHASE:
        # They still have a renewal available — route them to renew_enrollment
        # instead, since that's the cheaper option and should be offered first.
        raise HTTPException(
            status_code=400,
            detail="A discounted renewal is still available for this course.",
        )

    enrollment.status = EnrollmentStatus.ACTIVE.value
    enrollment.access_expires_at = datetime.now(timezone.utc) + timedelta(days=ACCESS_WINDOW_DAYS)
    enrollment.renewal_count = 0  # fresh cycle — one renewal becomes available again
    db.commit()
    db.refresh(enrollment)
    return enrollment


def mark_section_complete(db: Session, enrollment: Enrollment, section_id: int) -> Progress:
    if enrollment.status not in (EnrollmentStatus.ACTIVE.value, EnrollmentStatus.COMPLETED.value):
        raise HTTPException(status_code=403, detail="Course is locked — renew or repurchase to continue")

    existing = (
        db.query(Progress)
        .filter(Progress.enrollment_id == enrollment.id, Progress.section_id == section_id)
        .first()
    )
    if existing is not None:
        existing.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    progress = Progress(enrollment_id=enrollment.id, section_id=section_id)
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def expire_stale_enrollments(db: Session) -> int:
    now = datetime.now(timezone.utc)
    stale = (
        db.query(Enrollment)
        .filter(Enrollment.status == EnrollmentStatus.ACTIVE.value, Enrollment.access_expires_at < now)
        .all()
    )
    for enrollment in stale:
        enrollment.status = EnrollmentStatus.LOCKED.value

         # Notify the student their access is locked
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        can_renew = enrollment.renewal_count < MAX_RENEWALS_BEFORE_REPURCHASE
        notify_access_locked(db, enrollment.user_id, course.title, can_renew)

    db.commit()
    return len(stale)



def process_payment_action(
    db: Session, 
    user_id: int, 
    course_id: int, 
    action_type: str, 
    amount_paid: float, # Passed as float from the webhook router
    reference: str
):
    """
    Dispatcher called by the Paystack webhook.
    Verifies amounts strictly and routes to the correct enrollment state-machine function.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Course not found")

    # 1. STRICT AMOUNT VERIFICATION
    # Convert the float amount_paid back to Decimal for safe currency comparison
    paid_decimal = Decimal(str(amount_paid))

    if action_type == "new":
        if paid_decimal != course.price:
            raise ValueError(f"New enrollment amount mismatch. Expected {course.price}, got {paid_decimal}")
    elif action_type == "renew":
        if paid_decimal != course.renewal_price:
            raise ValueError(f"Renewal amount mismatch. Expected {course.renewal_price}, got {paid_decimal}")
    elif action_type == "repurchase":
        if paid_decimal != course.price:
            raise ValueError(f"Repurchase amount mismatch. Expected {course.price}, got {paid_decimal}")
    else:
        raise ValueError(f"Unknown action type: {action_type}")

    # 2. DISPATCH TO STATE MACHINE
    if action_type == "new":
        # create_enrollment will raise HTTPException(409) if they already have an enrollment
        create_enrollment(db, user_id, course_id)
        
    elif action_type in ("renew", "repurchase"):
        existing_enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )
        if not existing_enrollment:
            raise ValueError("No existing enrollment found to renew or repurchase")
            
        if action_type == "renew":
            # raises HTTPException(400) if state/renewal_count is invalid
            renew_enrollment(db, existing_enrollment)
        else:
            # raises HTTPException(400) if state is invalid
            repurchase_enrollment(db, existing_enrollment)