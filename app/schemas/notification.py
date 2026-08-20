from pydantic import BaseModel
from datetime import datetime
from typing import List


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    unread_count: int
    notifications: List[NotificationResponse]