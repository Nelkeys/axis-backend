import secrets
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import workos

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.core.security import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["Auth"])

workos_client = workos.WorkOSClient(
    api_key=settings.workos_api_key,
    client_id=settings.workos_client_id,
)


def _generate_referral_code() -> str:
    return "RVN" + secrets.token_hex(3).upper()


@router.get("/login")
def login(ref: str = None):
    # Pack the referral code into OAuth state so it survives the WorkOS redirect
    state = f"ref:{ref}" if ref else None

    authorization_url = workos_client.user_management.get_authorization_url(
        provider="authkit",
        redirect_uri=settings.workos_redirect_uri,
        state=state,
    )
    return RedirectResponse(authorization_url)


@router.get("/callback")
def callback(code: str, state: str = None, db: Session = Depends(get_db)):
    # Extract referral code from the OAuth state
    ref_code = None
    if state and state.startswith("ref:"):
        ref_code = state.split("ref:", 1)[1]

    try:
        auth_response = workos_client.user_management.authenticate_with_code(code=code)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired login code")

    workos_user = auth_response.user

    user = db.query(User).filter(User.workos_user_id == workos_user.id).first()
    if user is None:
        # ── REFERRAL CAPTURE ──────────────────────────────
        referrer_id = None
        if ref_code:
            referrer = db.query(User).filter(User.referral_code == ref_code).first()
            if referrer:
                referrer_id = referrer.id
        # ───────────────────────────────────────────────────

        user = User(
            workos_user_id=workos_user.id,
            email=workos_user.email,
            email_verified=workos_user.email_verified,
            referral_code=_generate_referral_code(),
            referred_by=referrer_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.email_verified != workos_user.email_verified:
            user.email_verified = workos_user.email_verified
            db.commit()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    response = RedirectResponse(url=f"{settings.frontend_url}/success.html")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=60 * 15,
    )
    return response


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if token is None:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(user.id)

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=60 * 15,
    )
    return {"status": "refreshed"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "logged out"}