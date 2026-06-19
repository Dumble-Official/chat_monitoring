import os
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.db_models import BanStatus, user_doc_template, log_doc

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("MONGO_DB_NAME", "chat_moderation")


class MongoService:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db     = self.client[DB_NAME]
        self.users  = self.db["users_moderation"]
        self.logs   = self.db["moderation_logs"]

    async def ensure_indexes(self):
        await self.users.create_index("user_id", unique=True)
        await self.logs.create_index("user_id")
        await self.logs.create_index("created_at")

    # ──────────────────────────────────────────────
    async def get_user(self, user_id: str) -> dict | None:
        return await self.users.find_one({"user_id": user_id})

    async def get_or_create_user(self, user_id: str) -> dict:
        user = await self.get_user(user_id)
        if not user:
            doc = user_doc_template(user_id)
            await self.users.insert_one(doc)
            return doc
        return user

    # ──────────────────────────────────────────────
    async def is_banned(self, user: dict) -> tuple[bool, str | None]:
        """Returns (is_banned, reason_message)."""
        status = user.get("ban_status", BanStatus.NONE)

        if status == BanStatus.PERMANENT:
            return True, "🚫 Your account has been permanently banned due to repeated violations."

        if status in (BanStatus.DAY, BanStatus.WEEK):
            expires = user.get("ban_expires_at")
            if expires and expires > datetime.now(timezone.utc):
                remaining = expires - datetime.now(timezone.utc)
                hours = int(remaining.total_seconds() // 3600)
                mins  = int((remaining.total_seconds() % 3600) // 60)
                return True, f"⛔ You are currently banned. Remaining time: {hours}h {mins}m."
            else:
                # Ban expired → lift it
                await self.lift_ban(user["user_id"])

        return False, None

    async def lift_ban(self, user_id: str):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "ban_status": BanStatus.NONE,
                "ban_expires_at": None,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

    # ──────────────────────────────────────────────
    async def apply_warning(self, user_id: str) -> tuple[int, BanStatus, datetime | None, str]:
        """
        Increments warning count, applies the right ban, returns
        (new_count, ban_status, ban_expires_at, message_to_user).
        """
        user = await self.get_or_create_user(user_id)
        now  = datetime.now(timezone.utc)
        new_count = user.get("warning_count", 0) + 1

        ban_status    = BanStatus.NONE
        ban_expires   = None
        msg_to_user   = ""

        if new_count == 1:
            ban_status  = BanStatus.DAY
            ban_expires = now + timedelta(days=1)
            msg_to_user = (
                "⚠️ Warning 1/3: Your message violated community guidelines. "
                "You are banned for 24 hours."
            )

        elif new_count == 2:
            ban_status  = BanStatus.WEEK
            ban_expires = now + timedelta(weeks=1)
            msg_to_user = (
                "⚠️ Warning 2/3: Repeated violation detected. "
                "You are banned for 7 days."
            )

        else:  # 3+
            ban_status  = BanStatus.PERMANENT
            ban_expires = None
            msg_to_user = (
                "🚫 Warning 3/3: You have been permanently banned "
                "due to repeated serious violations."
            )

        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "warning_count":  new_count,
                "ban_status":     ban_status,
                "ban_expires_at": ban_expires,
                "last_warning_at": now,
                "updated_at":     now,
            }},
            upsert=True,
        )

        return new_count, ban_status, ban_expires, msg_to_user

    # ──────────────────────────────────────────────
    async def save_log(
        self,
        user_id: str,
        message: str,
        label: str,
        confidence: float,
        warning_count_after: int,
        ban_applied: str | None,
    ):
        doc = log_doc(user_id, message, label, confidence, warning_count_after, ban_applied)
        await self.logs.insert_one(doc)

    # ──────────────────────────────────────────────
    async def reset_user(self, user_id: str):
        """Admin utility to reset a user's warnings and bans."""
        now = datetime.now(timezone.utc)
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "warning_count": 0,
                "ban_status": BanStatus.NONE,
                "ban_expires_at": None,
                "last_warning_at": None,
                "updated_at": now,
            }},
            upsert=True,
        )
