import hmac
import hashlib
import json
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.payment import PaystackEventLog
from app.models.user import User
from app.models.referral import CoinEntry
from app.services.enrollment_service import process_payment_action
from app.services.referral_service import grant_referral_reward

router = APIRouter(tags=["Webhooks"])


def verify_signature(payload_body: bytes, secret_key: str, signature: str | None) -> bool:
    """Verifies Paystack HMAC-SHA512 signature against the raw request body."""
    if not signature:
        return False

    expected_hash = hmac.new(
        secret_key.encode("utf-8"),
        payload_body,
        digestmod=hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(expected_hash, signature)


@router.post("/webhooks/paystack", status_code=200)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    # 1. Read raw bytes BEFORE any parsing — signature is computed over the raw body
    payload_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not verify_signature(payload_body, settings.paystack_secret_key, signature):
        # Return 200 so Paystack doesn't infinitely retry an invalid/forged request
        return {"status": "ignored", "reason": "invalid signature"}

    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        return {"status": "ignored", "reason": "invalid json"}

    # 2. Pull event_type and data ONCE — event_id lives inside "data", not at top level
    event_type = payload.get("event")
    data = payload.get("data", {})
    event_id = data.get("id")
    reference = data.get("reference")

    if not event_id or event_type != "charge.success":
        return {"status": "ignored", "reason": "not a success event"}

    # 3. Idempotency check
    already_processed = (
        db.query(PaystackEventLog)
        .filter(PaystackEventLog.event_id == str(event_id))
        .first()
    )
    if already_processed:
        return {"status": "ok", "message": "already processed"}

    # 4. Extract metadata + amount
    metadata = data.get("metadata", {})
    amount_paid_naira = data.get("amount", 0) / 100.0  # Paystack sends kobo

    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")
    action_type = metadata.get("action_type")  # "new" | "renew" | "repurchase"
    coins_applied = int(metadata.get("coins_applied", 0) or 0)

    if not all([user_id, course_id, action_type]):
        return {"status": "error", "message": "missing metadata"}

    user_id = int(user_id)
    course_id = int(course_id)

    # 5. Dispatch to enrollment service
    try:
        process_payment_action(
            db=db,
            user_id=user_id,
            course_id=course_id,
            action_type=action_type,
            amount_paid=amount_paid_naira,
            reference=reference,
            coins_applied=coins_applied,
        )
    except HTTPException as e:
        db.rollback()
        print(f"Webhook rejected by business logic: {e.detail}")
        return {"status": "ignored", "reason": e.detail}
    except ValueError as e:
        db.rollback()
        print(f"Webhook data validation failed: {e}")
        return {"status": "ignored", "reason": str(e)}
    except Exception as e:
        db.rollback()
        # Unexpected failure — surface a 500 so Paystack retries later
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    # 6. Coin & referral engine — runs only after enrollment succeeded
    try:
        if coins_applied > 0:
            db.add(CoinEntry(
                user_id=user_id,
                amount=-coins_applied,
                type="CHECKOUT_SPEND",
                reference=reference,
            ))

        payer = db.query(User).filter(User.id == user_id).first()
        if payer:
            grant_referral_reward(
                db=db,
                payer=payer,
                amount_paid_naira=amount_paid_naira,
                reference=reference,
            )

        # 7. Log success LAST, so idempotency record only exists once everything above worked
        db.add(PaystackEventLog(
            event_id=str(event_id),
            event_type=event_type,
            reference=reference,
            payload=payload,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post-processing failed: {e}")

    return {"status": "ok"}