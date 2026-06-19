from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.db_models import BanStatus


class ModerateRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier from your backend")
    message: str = Field(..., description="Chat message to moderate")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "message": "هأحرق الجيم لو المدرب كررها"
            }
        }


class ModerateResponse(BaseModel):
    user_id: str
    label: str                          # "Safe" | "Warning"
    confidence: float                   # probability of Warning class
    action: str                         # "allow" | "warn" | "ban_day" | "ban_week" | "ban_permanent"
    warning_count: int
    ban_status: BanStatus
    ban_expires_at: Optional[datetime]
    message_to_user: Optional[str]      # human-readable message for frontend


class UserStatusResponse(BaseModel):
    user_id: str
    warning_count: int
    ban_status: BanStatus
    ban_expires_at: Optional[datetime]
    last_warning_at: Optional[datetime]


class ResetUserRequest(BaseModel):
    user_id: str
