# app/services/payment_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from decimal import Decimal
import httpx

from app.config import settings
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus

PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"


def get_payment_amount(db: Session, user_id: int, course_id: int, action_type: str) -> Decimal:
    """
    Determines the correct price server-side.
    Never trust the frontend to tell you the price.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )

    if action_type == "new":
        if enrollment is not None:
            raise HTTPException(status_code=409, detail="Already enrolled. Use 'renew' or 'repurchase'.")
        return course.price

    elif action_type == "renew":
        if enrollment is None:
            raise HTTPException(status_code=404, detail="No enrollment to renew")
        if enrollment.status != EnrollmentStatus.LOCKED.value:
            raise HTTPException(status_code=400, detail="Only locked enrollments can be renewed")
        if enrollment.renewal_count >= 1:
            raise HTTPException(status_code=400, detail="Renewal used. Full repurchase required.")
        return course.renewal_price

    elif action_type == "repurchase":
        if enrollment is None:
            raise HTTPException(status_code=404, detail="No enrollment to repurchase")
        if enrollment.status != EnrollmentStatus.LOCKED.value:
            raise HTTPException(status_code=400, detail="Only locked enrollments can be repurchased")
        if enrollment.renewal_count < 1:
            raise HTTPException(status_code=400, detail="Discounted renewal still available.")
        return course.price

    else:
        raise HTTPException(status_code=400, detail="Invalid action_type")


async def initialize_paystack_transaction(
    email: str,
    amount_naira: Decimal,
    metadata: dict,
) -> dict:
    """
    Calls Paystack API to create a transaction.
    Returns the authorization_url and reference.
    """
    amount_kobo = int(float(amount_naira) * 100)

    headers = {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "amount": amount_kobo,
        "currency": "NGN",
        "metadata": metadata,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(PAYSTACK_INIT_URL, json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to initialize payment with Paystack")

    result = response.json()
    if not result.get("status"):
        raise HTTPException(status_code=502, detail=result.get("message", "Paystack error"))

    return {
        "authorization_url": result["data"]["authorization_url"],
        "reference": result["data"]["reference"],
    }