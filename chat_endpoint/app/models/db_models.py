from datetime import datetime, timezone
from enum import Enum


class BanStatus(str, Enum):
    NONE = "none"
    DAY = "day_ban"
    WEEK = "week_ban"
    PERMANENT = "permanent_ban"


# ───── Collection: users_moderation ─────
# {
#   _id: ObjectId,
#   user_id: str,                  ← unique
#   warning_count: int,            ← 0 / 1 / 2 / 3+
#   ban_status: BanStatus,
#   ban_expires_at: datetime | None,
#   last_warning_at: datetime | None,
#   created_at: datetime,
#   updated_at: datetime
# }

# ───── Collection: moderation_logs ─────
# {
#   _id: ObjectId,
#   user_id: str,
#   message: str,
#   label: "Safe" | "Warning",
#   confidence: float,
#   warning_count_after: int,
#   ban_applied: BanStatus | None,
#   created_at: datetime
# }


def user_doc_template(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "warning_count": 0,
        "ban_status": BanStatus.NONE,
        "ban_expires_at": None,
        "last_warning_at": None,
        "created_at": now,
        "updated_at": now,
    }


def log_doc(
    user_id: str,
    message: str,
    label: str,
    confidence: float,
    warning_count_after: int,
    ban_applied: str | None,
) -> dict:
    return {
        "user_id": user_id,
        "message": message,
        "label": label,
        "confidence": confidence,
        "warning_count_after": warning_count_after,
        "ban_applied": ban_applied,
        "created_at": datetime.now(timezone.utc),
    }
