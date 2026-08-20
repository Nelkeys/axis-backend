# app/routers/cron.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.services.enrollment_service import expire_stale_enrollments

router = APIRouter(prefix="/cron", tags=["Cron"])


@router.get("/run")
def run_cron_tasks(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Called by cron-job.org every 10-15 minutes.
    Serves as keepalive AND expires stale enrollments.
    Secured by a secret token in the header.
    """

    # Verify the cron secret
    cron_secret = request.headers.get("x-cron-secret")
    if not cron_secret or cron_secret != settings.cron_secret_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Run the expiry logic
    locked_count = expire_stale_enrollments(db)

    return {
        "status": "ok",
        "enrollments_locked": locked_count,
    }