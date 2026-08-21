from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.admin import AdminUser
from app.core.security import verify_password, create_admin_token
from app.config import settings

from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])

class AdminLoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def admin_login(data: AdminLoginRequest, response: Response, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.email == data.email).first()

    # Deliberately identical error for "no such admin" and "wrong password" —
    # never reveal which one it was, that's an account-enumeration leak.
    if admin is None or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_admin_token(admin.id)
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",  # stricter than student cookies — admin panel shouldn't be reachable cross-site at all
        max_age=60 * 60 * 8,
    )
    return {"status": "logged in"}
    

@router.get("/me")
def get_current_admin_session(current_admin: AdminUser = Depends(get_current_admin)):
    return {"id": current_admin.id, "email": current_admin.email}


@router.post("/logout")
def admin_logout(response: Response):
    response.delete_cookie("admin_token")
    return {"status": "logged out"}
