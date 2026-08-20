from fastapi import FastAPI, Depends
from app import models 
from app.routers import auth
from app.core.dependencies import get_current_user
from app.models.user import User
from app.routers import admin_auth
from app.routers import admin_courses
from app.routers import admin_content
from app.routers import enrollments
from app.routers import courses, payments, webhooks


app = FastAPI(title="Axis API")
app.include_router(admin_auth.router)
app.include_router(auth.router)
app.include_router(admin_courses.router)
app.include_router(admin_content.router)
app.include_router(enrollments.router)
app.include_router(courses.router)
app.include_router(payments.router)
app.include_router(webhooks.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}