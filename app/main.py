# app/main.py
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import models  # noqa: F401 — ensures all models are registered with Base
from app.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.routers import (
    # Student-facing
    auth,
    courses,
    enrollments,
    payments,
    quiz,
    profile,
    notifications,
    certificates,
    partner,
    student_wallet,
    # Admin-facing
    admin_auth,
    admin_courses,
    admin_content,
    admin_quiz,
    admin_dashboard,
    admin_referrals,
    admin_analytics,
    # System
    webhooks,
    cron,
)

# APP INITIALIZATION

app = FastAPI(
    title="Kalon Learn API",
    description="Backend for the Kalon Learn",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS — allow frontend origin only
origins = [
    "http://localhost:5173",
    "https://axisedu-admin.onrender.com",
    "https://admin-kalonlearn.onrender.com",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROUTERS — grouped by domain

# Student-facing routes
STUDENT_ROUTERS = [
    auth.router,
    courses.router,
    enrollments.router,
    payments.router,
    quiz.router,
    profile.router,
    notifications.router,
    certificates.router,
    partner.router,
    student_wallet.router,
]

# Admin-facing routes
ADMIN_ROUTERS = [
    admin_auth.router,
    admin_courses.router,
    admin_content.router,
    admin_quiz.router,
    admin_dashboard.router,
    admin_referrals.router,
    admin_analytics.router,
]

# System routes (webhooks, cron)
SYSTEM_ROUTERS = [
    webhooks.router,
    cron.router,
]

for router in STUDENT_ROUTERS + ADMIN_ROUTERS + SYSTEM_ROUTERS:
    app.include_router(router)

# CORE SYSTEM ENDPOINTS
@app.get("/health", tags=["System"])
def health_check():
    """Check if the API service is up and running."""
    return {"status": "ok"}


@app.get("/me", tags=["System"])
def read_current_user(current_user: User = Depends(get_current_user)):
    """Quick identity check for the currently authenticated student."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": getattr(current_user, "name", None),
    }
