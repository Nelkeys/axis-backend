from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns the current student's profile."""
    return current_user


@router.patch("", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update name and/or phone.
    Only updates fields that are explicitly provided.
    """
    if data.name is not None:
        current_user.name = data.name
    if data.phone is not None:
        current_user.phone = data.phone

    db.commit()
    db.refresh(current_user)
    return current_user