from fastapi import Depends, FastAPI

from app import models
from app.core.dependencies import get_current_user
from app.models.user import User
from app.routers import (
    admin_auth,
    admin_content,
    admin_courses,
    admin_quiz,
    auth,
    certificates,
    courses,
    cron,
    enrollments,
    payments,
    quiz,
    webhooks,
)

# Initialize FastAPI App
app = FastAPI(title="Axis API")

ROUTERS = [
    auth.router,
    admin_auth.router,
    courses.router,
    admin_courses.router,
    admin_content.router,
    enrollments.router,
    payments.router,
    webhooks.router,
    quiz.router,
    admin_quiz.router,
    certificates.router,
    cron.router,
]

for router in ROUTERS:
    app.include_router(router)


# Core Endpoints
@app.get("/health", tags=["System"])
def health_check():
    """Check if the API service is up and running."""
    return {"status": "ok"}


@app.get("/me", tags=["User"])
def read_current_user(current_user: User = Depends(get_current_user)):
    """Fetch profile data for the currently authenticated user."""
    return {"id": current_user.id, "email": current_user.email}
