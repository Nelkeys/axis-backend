import hmac
import hashlib
import json
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.payment import PaystackEventLog
from app.services.enrollment_service import process_payment_action # We'll define this below

router = APIRouter(tags=["Webhooks"])

def verify_signature(payload_body: bytes, secret_key: str, signature: str) -> bool:
    """Verifies Paystack HMAC-SHA512 signature."""
    if not signature:
        return False
    
    # Paystack signs the exact raw bytes sent
    hash = hmac.new(
        secret_key.encode('utf-8'), 
        payload_body, 
        digestmod=hashlib.sha512
    ).hexdigest()
    
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(hash, signature)

@router.post("/webhooks/paystack", status_code=200)
async def paystack_webhook(
    request: Request, 
    db: Session = Depends(get_db)
):
    # 1. Read the raw body BEFORE doing anything else
    payload_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    # 2. Verify the signature
    if not verify_signature(payload_body, settings.paystack_secret_key, signature):
        # Do not return 401/403 here, just return 200 to stop Paystack from infinitely retrying
        # Log it internally if you have an alerting system (Sentry, etc.)
        return {"status": "ignored", "reason": "invalid signature"}

    # 3. Parse the JSON payload safely now that we know it's authentic
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        return {"status": "ignored", "reason": "invalid json"}

    # 4. Check Idempotency (Have we seen this event_id before?)
    event_id = payload.get("id")
    event_type = payload.get("event")
    
    if not event_id or event_type != "charge.success":
        return {"status": "ignored", "reason": "not a success event"}

    existing_event = db.query(PaystackEventLog).filter(PaystackEventLog.event_id == str(event_id)).first()
    if existing_event:
        # We already processed this. Return 200 to tell Paystack we got it.
        return {"status": "ok", "message": "already processed"}

    # 5. Extract Data & Verify Amount
    data = payload.get("data", {})
    metadata = data.get("metadata", {})
    
    # Paystack sends amounts in KOBO (e.g., 350000 for N3,500.00)
    amount_paid_kobo = data.get("amount", 0)
    amount_paid_naira = amount_paid_kobo / 100.0
    
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")
    action_type = metadata.get("action_type") # "new", "renew", or "repurchase"

    if not all([user_id, course_id, action_type]):
        return {"status": "error", "message": "missing metadata"}

    # 6. Dispatch to Enrollment Service
    try:
        process_payment_action(
            db=db,
            user_id=int(user_id),
            course_id=int(course_id),
            action_type=action_type,
            amount_paid=amount_paid_naira,
            reference=data.get("reference")
        )
    except HTTPException as e:
        # Business logic rejection (e.g., 409 Already Enrolled, 400 Invalid State)
        # Return 200 to Paystack so it stops retrying, but log the rejection
        print(f"Webhook rejected by business logic: {e.detail}")
        return {"status": "ignored", "reason": e.detail}
    except ValueError as e:
        # Data validation failure (e.g., amount mismatch, unknown action)
        # Return 200 to stop retries, this is a permanent client-side failure
        print(f"Webhook data validation failed: {str(e)}")
        return {"status": "ignored", "reason": str(e)}
    except Exception as e:
        # Unexpected error (e.g., DB connection dropped)
        # Raise 500 so Paystack knows it failed and retries later
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    # 7. Log the successful processing to guarantee idempotency
    log_entry = PaystackEventLog(
        event_id=str(event_id),
        event_type=event_type,
        reference=data.get("reference"),
        payload=payload
    )
    db.add(log_entry)
    db.commit()

    return {"status": "ok"}