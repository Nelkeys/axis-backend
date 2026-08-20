from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.models.admin import AdminUser
import jwt

from app.database import get_db
from app.models.user import User
from app.core.security import decode_token

def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    token = request.cookies.get("admin_token")
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated as admin")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Admin session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    if payload.get("type") != "admin_access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    admin_id = payload.get("sub")
    admin = db.query(AdminUser).filter(AdminUser.id == int(admin_id)).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Admin not found")

    return admin

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token")

    if payload.get("type") != "access":
        # Someone tried to use a refresh token as an access token.
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user